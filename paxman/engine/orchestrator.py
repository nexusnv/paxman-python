"""Engine orchestrator — runs the recognition → validation pipeline."""

from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass
from importlib.metadata import version as _get_version
from typing import Any

from paxman.core.capability import Capability
from paxman.core.capability_contract import CapabilityContract
from paxman.core.discovery import (
    freeze_registry,
    get_capability,
    get_recognition_revision,
)
from paxman.core.domain import (
    Candidate,
    Grammar,
    GrammarRule,
    Mention,
    RecognitionMatch,
    RecognizedRep,
    Resolution,
    Rule,
    ScanResult,
    VersionStamp,
)
from paxman.core.errors import (
    CapabilityError,
    ContractError,
    MultipleMentionsError,
    RecognitionError,
    ValidationError,
)
from paxman.core.extensions import get_extended_grammars, get_extended_rules
from paxman.core.grammar.engine_loop import run_matchers_with_context
from paxman.core.grammar.matchers.candidates import (
    CandidatesMatcher,
    get_flat_for_matcher,
)
from paxman.core.grammar.scan_context import ScanContext


def _resolve_version() -> str:
    """Resolve the installed paxman package version."""
    try:
        return _get_version("paxman")
    except (ImportError, ValueError, TypeError, AttributeError, RuntimeError):
        return "0.2.0"


PAXMAN_VERSION = _resolve_version()


@dataclass(frozen=True)
class ExecutionResult:
    """Final output from the orchestration pipeline."""

    status: Resolution
    canonicalized_value: str | None
    candidates: tuple[Candidate, ...]
    contract: CapabilityContract
    version_stamp: VersionStamp
    span: tuple[int, int] | None = None


def run_capability(text: str, contract: CapabilityContract) -> ExecutionResult:
    """Run the full pipeline: recognition → validation → result."""
    freeze_registry()
    capability = get_capability(contract.capability_name)

    shipped_grammars = capability.get_grammars()
    all_grammars = [
        *shipped_grammars,
        *get_extended_grammars(capability.name),
    ]
    _assert_unique_names("grammar", all_grammars)
    semantics_by_name = {g.name: g.semantics for g in all_grammars}
    for g in all_grammars:
        for m in getattr(g, "matchers", None) or ():
            if (
                isinstance(m, CandidatesMatcher)
                and m.candidate_names
                and m.candidate_semantics
            ):
                for cname, csem in zip(
                    m.candidate_names,
                    m.candidate_semantics,
                    strict=True,
                ):
                    semantics_by_name[cname] = csem
    all_rules = [
        *capability.get_rules(),
        *_activated_rules(capability, contract, semantics_by_name),
    ]
    _assert_unique_names("rule", all_rules)
    _validate_affinity(semantics_by_name, all_rules)
    recognitions = _recognize(
        text,
        all_grammars,
        [g.name for g in shipped_grammars],
        contract,
    )
    had_recognitions = len(recognitions) > 0

    rules = _filter_rules(all_rules, contract)
    single_value_by_grammar_name = {g.name: g.single_value for g in all_grammars}
    for g in all_grammars:
        for m in getattr(g, "matchers", None) or ():
            if isinstance(m, CandidatesMatcher) and m.candidate_names:
                for cname in m.candidate_names:
                    single_value_by_grammar_name[cname] = g.single_value
    collected = _collect_candidates(capability, recognitions, rules, semantics_by_name)
    _enforce_single_value_invariant(collected, single_value_by_grammar_name)

    keep_dup = False
    for g in all_grammars:
        for m in getattr(g, "matchers", None) or ():
            if isinstance(m, CandidatesMatcher) and m.strategy == "all":
                keep_dup = True
                break
    candidates = _dedup_candidates(collected, keep_duplicate_spans=keep_dup)

    status = _determine_status(candidates, had_recognitions)
    canonical_value = _extract_canonical_value(candidates, status)
    version_stamp = VersionStamp(
        paxman_version=PAXMAN_VERSION, recognition_revision=get_recognition_revision()
    )

    return ExecutionResult(
        status=status,
        canonicalized_value=canonical_value,
        candidates=tuple(candidates),
        contract=contract,
        version_stamp=version_stamp,
        span=(
            candidates[0].span
            if candidates and len({c.value for c in candidates}) == 1
            else None
        ),
    )


def run_scan(text: str, contracts: Sequence[CapabilityContract]) -> ScanResult:
    """Batch scan — one substrate pass, per-capability Mention records.

    This is the engine half of the ``scan()`` API (ADR-009). The substrate
    (:class:`ScanContext`) is built once and reused for every contract in
    the batch; mentions are maximal clusters of recognitions under the
    existing total order + containment policy.
    """
    freeze_registry()
    # One substrate pass for the whole batch.
    ctx = ScanContext.of(text)
    mentions: dict[str, tuple[Mention, ...]] = {}
    for contract in contracts:
        capability = get_capability(contract.capability_name)
        shipped_grammars = capability.get_grammars()
        all_grammars = [
            *shipped_grammars,
            *get_extended_grammars(capability.name),
        ]
        _assert_unique_names("grammar", all_grammars)
        semantics_by_name = {g.name: g.semantics for g in all_grammars}
        for g in all_grammars:
            for m in getattr(g, "matchers", None) or ():
                if (
                    isinstance(m, CandidatesMatcher)
                    and m.candidate_names
                    and m.candidate_semantics
                ):
                    for cname, csem in zip(
                        m.candidate_names,
                        m.candidate_semantics,
                        strict=True,
                    ):
                        semantics_by_name[cname] = csem
        all_rules = [
            *capability.get_rules(),
            *_activated_rules(capability, contract, semantics_by_name),
        ]
        _assert_unique_names("rule", all_rules)
        _validate_affinity(semantics_by_name, all_rules)
        recognitions = _recognize(
            text,
            all_grammars,
            [g.name for g in shipped_grammars],
            contract,
            scan_context=ctx,
        )
        mentions[contract.capability_name] = _recognitions_to_mentions(recognitions)
    return ScanResult(text=text, mentions=mentions)


def _assert_unique_names(kind: str, items: Sequence[Grammar[Any] | Rule[Any]]) -> None:
    """Fail fast when a composed grammar or rule name is duplicated.

    Shipped names must never be shadowed or duplicated by community
    extensions: a duplicate would make provenance attribution ambiguous
    (routing is semantic, but names remain the audit identity), so reject it
    at composition time (D4).
    """
    names = [item.name for item in items]
    duplicates = sorted({name for name in names if names.count(name) > 1})
    if duplicates:
        raise CapabilityError(f"Duplicate {kind} name(s): {duplicates}")


def _extra_grammars_of(contract: CapabilityContract) -> tuple[str, ...]:
    """Resolve a contract's opt-in community grammar names (ADR-0007).

    ``CapabilityContract`` always defines ``extra_grammars``; a legacy or
    duck-typed contract that does not inherit it violates the contract surface
    and must fail fast with :class:`ContractError` -- never a raw
    ``AttributeError`` -- pointing the caller at ``CapabilityContract``.
    """
    extra = getattr(contract, "extra_grammars", None)
    if extra is None:
        name = getattr(contract, "capability_name", type(contract).__name__)
        raise ContractError(
            f"Contract {name!r} lacks 'extra_grammars'; "
            "contracts must inherit CapabilityContract (ADR-0007)."
        )
    return tuple(extra)


def _recognize(
    text: str,
    all_grammars: Sequence[Grammar[Any]],
    shipped_names: Sequence[str],
    contract: CapabilityContract,
    *,
    scan_context: ScanContext | None = None,
) -> list[RecognizedRep[Any]]:
    """Run active grammars, dedup contained matches per grammar, and order.

    Every match is validated against the span contract (bounds within the
    input, ``raw_text`` equal to the matched slice) before dedup; a grammar
    returning a malformed match raises ``RecognitionError`` naming the
    grammar. The engine owns all cross-match policy: containment dedup runs
    strictly within a single grammar's output (never across grammars, so
    cross-grammar ambiguity stays observable), and recognitions are emitted
    in the total order (start, end, active set index, grammar name) where the
    index follows the composed active set: ``contract.active_grammars``
    first, then any opt-in ``contract.extra_grammars`` names (unknown extra
    names are silently skipped, D4).

    A contract whose ``active_grammars`` is ``None`` (the base-class default)
    falls back to ``shipped_names`` — every shipped grammar in
    ``get_grammars()`` declaration order — so adding a shipped grammar to a
    capability activates it with no contract edit. Community grammars stay
    opt-in via ``extra_grammars`` in both cases.

    ``scan_context`` is the shared substrate for ``scan()`` batch calls
    (ADR-009): when provided the engine reuses it for compiled matchers
    instead of constructing a new :class:`ScanContext` per grammar, so one
    substrate pass serves all capabilities in the batch.
    """
    supported_names = {g.name for g in all_grammars}
    extra_grammars = _extra_grammars_of(contract)
    declared = contract.active_grammars
    active_source = shipped_names if declared is None else declared
    # Deduplicate contract names, keeping first occurrence: each supported
    # grammar runs at most once and grammar_index stays aligned with
    # active_grammars (a duplicate contract entry must not double-run it).
    # Community grammars opt in via extra_grammars and keep their declared
    # order after the shipped slots.
    active_names = list(
        dict.fromkeys(
            n for n in [*active_source, *extra_grammars] if n in supported_names
        )
    )
    grammar_index = {name: i for i, name in enumerate(active_names)}
    by_name = {g.name: g for g in all_grammars}
    active_grammars = [by_name[name] for name in active_names]

    # Shared substrate (ADR-009): one ScanContext for the whole batch.
    # Lazy-initialize when scan() passes a context; single-capability
    # canonicalize() still creates one locally.
    shared_ctx = scan_context if scan_context is not None else ScanContext.of(text)
    # Reuse shared word_spans/text without forcing grammars to change
    # their recognize(text) surface: compiled matchers go through the
    # engine loop with the shared context, legacy grammars keep their
    # own recognize path (they internally call ScanContext.of but that
    # is bounded to one extra construction per legacy grammar).
    ordered: list[tuple[int, int, int, str, RecognitionMatch[Any]]] = []
    for grammar in active_grammars:
        # compat shim: if grammar exposes compiled matchers, delegate to
        # engine-owned loop (pass contract for requires_features filtering per ADR §13)
        _matchers = getattr(grammar, "matchers", None)
        if _matchers:
            try:
                matches = run_matchers_with_context(shared_ctx, [grammar], contract)
            except (
                re.error,
                ValueError,
                TypeError,
                AttributeError,
                RuntimeError,
                AssertionError,
            ) as exc:
                raise RecognitionError(
                    rule=grammar.name,
                    message=f"Grammar failed: {exc}",
                    original_error=exc,
                ) from exc
        else:
            try:
                matches = grammar.recognize(text)
            except (
                re.error,
                ValueError,
                TypeError,
                AttributeError,
                RuntimeError,
                AssertionError,
            ) as exc:
                raise RecognitionError(
                    rule=grammar.name,
                    message=f"Grammar failed: {exc}",
                    original_error=exc,
                ) from exc
        for match in matches:
            if not 0 <= match.start <= match.end <= len(text):
                raise RecognitionError(
                    rule=grammar.name,
                    message=(
                        f"Grammar '{grammar.name}' returned a match with span "
                        f"[{match.start}, {match.end}) outside the input "
                        f"bounds [0, {len(text)}]"
                    ),
                )
            if match.raw_text != text[match.start : match.end]:
                raise RecognitionError(
                    rule=grammar.name,
                    message=(
                        f"Grammar '{grammar.name}' returned a match whose "
                        f"raw_text {match.raw_text!r} does not equal "
                        f"text[{match.start}:{match.end}] = "
                        f"{text[match.start : match.end]!r}"
                    ),
                )
        keep_equal = False
        _ms = getattr(grammar, "matchers", None)
        if _ms:
            for _m in _ms:
                if isinstance(_m, CandidatesMatcher) and _m.strategy == "all":
                    keep_equal = True
                    break
        deduped = _dedup_spans(matches, keep_equal=keep_equal)
        cand_matcher = None
        for _m in getattr(grammar, "matchers", None) or ():
            if isinstance(_m, CandidatesMatcher) and _m.candidate_names:
                cand_matcher = _m
                break
        if cand_matcher is not None:
            flat = get_flat_for_matcher(cand_matcher)
            # Key flat by span — flat is sorted by (start, end, idx) while deduped is
            # sorted by (start, -length); index pairing would misattribute when
            # candidates produce same-start/different-end spans (future IBAN/ISBN).
            from collections import defaultdict, deque

            span_to_indices: dict[tuple[int, int], deque[int]] = defaultdict(deque)
            for s, e, idx in flat:
                span_to_indices[(s, e)].append(idx)
            for match in deduped:
                key = (match.start, match.end)
                cand_idx = 0
                cand_name = grammar.name
                dq = span_to_indices.get(key)
                if dq is not None and dq:
                    cand_idx = dq.popleft()
                    if cand_idx < len(cand_matcher.candidate_names):
                        cand_name = cand_matcher.candidate_names[cand_idx]
                    else:
                        cand_idx = 0
                        cand_name = grammar.name
                ordered.append((match.start, match.end, cand_idx, cand_name, match))
        else:
            for match in deduped:
                ordered.append(
                    (
                        match.start,
                        match.end,
                        grammar_index[grammar.name],
                        grammar.name,
                        match,
                    )
                )

    ordered.sort(key=lambda item: (item[0], item[1], item[2], item[3]))

    recognitions: list[RecognizedRep[Any]] = []
    for start, end, _index, grammar_name, match in ordered:
        grammar_ref = GrammarRule(
            capability_name=contract.capability_name,
            grammar_name=grammar_name,
        )
        recognitions.append(
            RecognizedRep(
                notation=match.notation,
                contract=contract,
                grammar=grammar_ref,
                start=start,
                end=end,
                raw_text=match.raw_text,
            )
        )
    return recognitions


def _dedup_spans(
    matches: list[RecognitionMatch[Any]],
    *,
    keep_equal: bool = False,
) -> list[RecognitionMatch[Any]]:
    """Drop matches fully contained in a longer match from the SAME grammar.

    ``longer wins``: when two matches from one grammar overlap, the match
    covering more of the input survives; an exact tie keeps the first unless
    ``keep_equal`` is True (candidates strategy "all" — keep duplicate spans
    for AMBIGUOUS preservation).
    Runs strictly within one grammar's output — overlapping matches from
    different grammars are preserved so cross-grammar ambiguity stays
    observable.
    """
    ordered = sorted(matches, key=lambda m: (m.start, -(m.end - m.start)))
    kept: list[RecognitionMatch[Any]] = []
    for match in ordered:
        if keep_equal:
            if any(
                other.start <= match.start
                and match.end <= other.end
                and (other.start < match.start or match.end < other.end)
                for other in kept
            ):
                continue
        else:
            if any(
                other.start <= match.start and match.end <= other.end for other in kept
            ):
                continue
        kept.append(match)
    return kept


def _filter_rules(
    all_rules: list[Rule[Any]], contract: CapabilityContract
) -> list[Rule[Any]]:
    """Return rules based on pinning, exclusion, year, and feature filters.

    When pinned_rules is set, ONLY those rules run (excluded_rules is ignored).

    Feature gating runs LAST, after pin/exclude and year selection: a rule
    whose required contract features are present-but-false is dropped (a
    recognized input then yields INVALID), and a rule naming a feature the
    contract does not have is a metadata/contract mismatch that fails fast
    with ContractError rather than silently excluding the rule.
    """
    if contract.pinned_rules is not None:
        pinned_set = set(contract.pinned_rules)
        known_names = {r.name for r in all_rules}
        unknown = pinned_set - known_names
        if unknown:
            raise ContractError(f"Unknown pinned rule(s): {sorted(unknown)}")
        active_rules = [r for r in all_rules if r.name in pinned_set]
    else:
        excluded = set(contract.excluded_rules)
        known_names = {r.name for r in all_rules}
        unknown = excluded - known_names
        if unknown:
            raise ContractError(f"Unknown excluded rule(s): {sorted(unknown)}")
        active_rules = [r for r in all_rules if r.name not in excluded]

    if contract.year is not None:
        active_rules = [
            r for r in active_rules if r.provenance.publication_year <= contract.year
        ]

    for rule in active_rules:
        missing = [
            feature
            for feature in rule.requires_features
            if not hasattr(contract, feature)
        ]
        if missing:
            raise ContractError(
                f"Rule {rule.name!r} requires missing contract feature(s): "
                f"{sorted(missing)}"
            )

    return [
        r
        for r in active_rules
        if all(getattr(contract, feature, False) for feature in r.requires_features)
    ]


def _validate_affinity(
    semantics_by_name: dict[str, str], rules: list[Rule[Any]]
) -> None:
    """Ensure every rule's declared semantics exist in the composition.

    The composition covers shipped and community grammars alike; a dangling
    semantics would silently exclude a rule from ever running, so fail
    fast at pipeline start rather than producing a wrong (e.g. INVALID) result.
    """
    known_semantics = set(semantics_by_name.values())
    for rule in rules:
        unknown = [s for s in rule.target_semantics if s not in known_semantics]
        if unknown:
            raise ContractError(
                f"Rule {rule.name!r} declares unknown semantics "
                f"{sorted(unknown)}; available: {sorted(known_semantics)}"
            )


def _collect_candidates(
    capability: Capability[Any],
    recognitions: list[RecognizedRep[Any]],
    rules: list[Rule[Any]],
    semantics_by_name: dict[str, str],
) -> list[tuple[Candidate, RecognizedRep[Any]]]:
    """Match recognitions against rules and collect (candidate, source) pairs.

    Routes each recognition only to rules whose ``target_semantics`` includes
    the producing grammar's semantics, formats each validated value through
    the capability's ``format_value()`` seam, then returns each
    ``Candidate`` together with the ``RecognizedRep`` that produced it. The
    paired rep carries the recognition span used by
    ``_enforce_single_value_invariant`` to attribute candidates to their source
    mention; dedup runs later in ``_dedup_candidates``.

    The ``semantics_by_name[grammar_name]`` lookup cannot KeyError:
    recognitions are produced only by grammars in the composed ``all_grammars``
    (``_recognize`` filters against ``supported_names``), the same list the map
    is built from.
    """
    collected: list[tuple[Candidate, RecognizedRep[Any]]] = []
    for recognition in recognitions:
        grammar_name = recognition.grammar.grammar_name
        for rule in rules:
            if semantics_by_name[grammar_name] not in rule.target_semantics:
                continue
            try:
                if rule.matches(recognition.notation, recognition.contract):
                    canonical = rule.normalize(
                        recognition.notation, recognition.contract
                    )
                    value = capability.format_value(
                        canonical,
                        recognition.contract.output_format,
                        recognition.notation,
                    )
                    collected.append(
                        (
                            Candidate(
                                value=value,
                                recognition_rule=grammar_name,
                                validation_rule=rule.name,
                                provenance=(rule.provenance,),
                                span=(recognition.start, recognition.end),
                            ),
                            recognition,
                        )
                    )
            except Exception as exc:
                raise ValidationError(
                    rule=rule.name,
                    message=f"Validation failed: {exc}",
                    original_error=exc,
                ) from exc
    return collected


def _enforce_single_value_invariant(
    collected: Sequence[tuple[Candidate, RecognizedRep[Any]]],
    single_value_by_grammar_name: dict[str, bool],
) -> None:
    """Fail fast on un-segmented multi-entity input (ADR-0004).

    Only grammars that opt in via ``Grammar.single_value`` are checked. For those,
    candidate spans are clustered into mentions: spans that overlap or contain one
    another are one logical mention. A single mention yielding several values is
    genuine single-mention ambiguity and stays ``AMBIGUOUS``. Two or more
    *separate* (non-overlapping) mentions that resolve to different values are
    un-segmented multi-entity input and raise ``MultipleMentionsError``.

    Overlap clustering is what lets the invariant spare the cases it must not
    touch: cross-grammar reads of one span (one cluster, many values →
    ambiguous), and a grammar that emits several overlapping parses of one mention
    (one cluster). Grammars that deliberately emit multiple spans for one logical
    mention (e.g. a span-bearing seam probe) leave ``single_value`` False and are
    exempt from the check entirely.
    """
    if not collected:
        return
    clusters: list[set[tuple[int, int]]] = []
    values_by_span: dict[tuple[int, int], set[str]] = {}
    for candidate, rep in collected:
        if not single_value_by_grammar_name.get(rep.grammar.grammar_name, False):
            continue
        span = (rep.start, rep.end)
        values_by_span.setdefault(span, set()).add(candidate.value)
        overlapping_clusters = [
            cluster
            for cluster in clusters
            if any(_spans_overlap(span, other) for other in cluster)
        ]
        if overlapping_clusters:
            # A span may overlap several clusters; merge all of them so one
            # logical mention is never split (which would raise a false
            # MultipleMentionsError).
            merged: set[tuple[int, int]] = {span}
            for cluster in overlapping_clusters:
                merged.update(cluster)
                clusters.remove(cluster)
            clusters.append(merged)
        else:
            clusters.append({span})
    if len(clusters) <= 1:
        return
    distinct_values: set[str] = set()
    for cluster in clusters:
        for span in cluster:
            distinct_values |= values_by_span[span]
    if len(distinct_values) > 1:
        raise MultipleMentionsError(
            f"Input contained {len(clusters)} distinct mentions resolving to "
            f"{len(distinct_values)} distinct canonical values "
            f"({sorted(distinct_values)}). Paxman resolves one entity per call; "
            "split the input into separate canonicalize() calls. "
            "See docs/recipes/segmentation.md for the split-then-canonicalize pattern."
        )


def _spans_overlap(a: tuple[int, int], b: tuple[int, int]) -> bool:
    """Whether two half-open spans share any character position."""
    return a[0] < b[1] and b[0] < a[1]


def _cluster_recognitions(
    recognitions: Sequence[RecognizedRep[Any]],
) -> list[list[RecognizedRep[Any]]]:
    """Cluster recognitions into maximal overlapping groups (mentions).

    Uses the same overlap+containment policy as the single-value invariant:
    any two recognitions whose spans overlap belong to the same logical
    mention; transitive overlap merges clusters. Input is assumed already in
    total order (start, end, ...); output clusters preserve that order and
    are sorted by their covering span.
    """
    clusters: list[list[RecognizedRep[Any]]] = []
    for rec in recognitions:
        span = (rec.start, rec.end)
        overlapping = [
            c
            for c in clusters
            if any(_spans_overlap(span, (r.start, r.end)) for r in c)
        ]
        if overlapping:
            merged: list[RecognizedRep[Any]] = [rec]
            for c in overlapping:
                merged.extend(c)
                clusters.remove(c)
            # Keep total-order determinism inside the merged cluster.
            merged.sort(key=lambda r: (r.start, r.end, r.grammar.grammar_name))
            clusters.append(merged)
        else:
            clusters.append([rec])
    # Sort clusters by covering span for deterministic mention order.
    clusters.sort(key=lambda c: (min(r.start for r in c), max(r.end for r in c)))
    return clusters


def _recognitions_to_mentions(
    recognitions: Sequence[RecognizedRep[Any]],
) -> tuple[Mention, ...]:
    """Map recognitions to Mention records via maximal-cluster policy."""
    if not recognitions:
        return ()
    clusters = _cluster_recognitions(list(recognitions))
    mentions: list[Mention] = []
    for cluster in clusters:
        # Covering span of the cluster
        min_start = min(r.start for r in cluster)
        max_end = max(r.end for r in cluster)
        first = cluster[0]
        mentions.append(
            Mention(
                span=(min_start, max_end),
                grammar=first.grammar.grammar_name,
                notation=first.notation,
                candidates=None,
            )
        )
    mentions.sort(key=lambda m: (m.span[0], m.span[1], m.grammar))
    return tuple(mentions)


def _dedup_candidates(
    collected: Sequence[tuple[Candidate, RecognizedRep[Any]]],
    *,
    keep_duplicate_spans: bool = False,
) -> list[Candidate]:
    if keep_duplicate_spans:
        return [c for c, _ in collected]
    seen: set[tuple[str, str, str]] = set()
    deduped: list[Candidate] = []
    for candidate, _rep in collected:
        key = (
            candidate.value,
            candidate.recognition_rule,
            candidate.validation_rule,
        )
        if key not in seen:
            seen.add(key)
            deduped.append(candidate)
    return deduped


def _determine_status(
    candidates: Sequence[Candidate], had_recognitions: bool
) -> Resolution:
    """Determine resolution status from candidates."""
    if not candidates:
        if had_recognitions:
            return Resolution.INVALID
        return Resolution.MISSING
    values = {c.value for c in candidates}
    if len(values) == 1:
        return Resolution.SUCCESS
    return Resolution.AMBIGUOUS


def _extract_canonical_value(
    candidates: Sequence[Candidate], status: Resolution
) -> str | None:
    """Extract canonical value if status is SUCCESS."""
    if status == Resolution.SUCCESS and candidates:
        return candidates[0].value
    return None


def _activated_rules(
    capability: Capability[Any],
    contract: CapabilityContract,
    semantics_by_name: dict[str, str],
) -> list[Rule[Any]]:
    """Community rules opt in like grammars: a rule runs only when the
    contract's ``extra_grammars`` resolve to one of its ``target_semantics``.

    An unknown extra name keeps its own string as the semantics key, so a
    rule declaring it (a dangling target) still fails fast in affinity
    validation instead of being silently excluded. An un-opted community
    rule — even one targeting a shipped grammar — never affects results,
    keeping extension behavior deterministic per contract.
    """
    extra_grammars = set(_extra_grammars_of(contract))
    extra_semantics = {semantics_by_name.get(n, n) for n in extra_grammars}
    return [
        rule
        for rule in get_extended_rules(capability.name)
        if extra_semantics & rule.target_semantics
    ]
