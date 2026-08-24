"""Engine orchestrator — runs the recognition → validation pipeline."""

from __future__ import annotations

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
    RecognitionMatch,
    RecognizedRep,
    Resolution,
    Rule,
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
from paxman.core.grammar.engine_loop import _run_matchers


def _resolve_version() -> str:
    """Resolve the installed paxman package version."""
    try:
        return _get_version("paxman")
    except Exception:
        return "0.1.0"


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
    collected = _collect_candidates(capability, recognitions, rules, semantics_by_name)
    _enforce_single_value_invariant(collected, single_value_by_grammar_name)

    candidates = _dedup_candidates(collected)

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

    ordered: list[tuple[int, int, int, str, RecognitionMatch[Any]]] = []
    for grammar in active_grammars:
        # compat shim: if grammar exposes compiled matchers, delegate to
        # engine-owned loop
        if hasattr(grammar, "matchers") and grammar.matchers:  # type: ignore[attr-defined]
            try:
                matches = _run_matchers(text, [grammar])
            except Exception as exc:
                raise RecognitionError(
                    rule=grammar.name,
                    message=f"Grammar failed: {exc}",
                    original_error=exc,
                ) from exc
        else:
            try:
                matches = grammar.recognize(text)
            except Exception as exc:
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
        for match in _dedup_spans(matches):
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
) -> list[RecognitionMatch[Any]]:
    """Drop matches fully contained in a longer match from the SAME grammar.

    ``longer wins``: when two matches from one grammar overlap, the match
    covering more of the input survives; an exact tie keeps the first.
    Runs strictly within one grammar's output — overlapping matches from
    different grammars are preserved so cross-grammar ambiguity stays
    observable.
    """
    ordered = sorted(matches, key=lambda m: (m.start, -(m.end - m.start)))
    kept: list[RecognitionMatch[Any]] = []
    for match in ordered:
        if any(other.start <= match.start and match.end <= other.end for other in kept):
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


def _dedup_candidates(
    collected: Sequence[tuple[Candidate, RecognizedRep[Any]]],
) -> list[Candidate]:
    """Drop identical (value, recognition_rule, validation_rule) tuples.

    Provenance is deterministic per (rule, grammar) pair, so collapsing on this
    key preserves all information while keeping the candidate multiset stable
    under any future over-declaration of ``target_semantics``.
    """
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
