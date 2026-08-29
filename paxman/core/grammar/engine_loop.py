"""Engine-owned match loop L0 (lazy views) → T0 anchors → T1 shape match.

B1 common-word suppression; see _VIEW_REGISTRY country_normalized."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from paxman.core.domain import RecognitionMatch
from paxman.core.grammar.boundary_spec import check_boundary
from paxman.core.grammar.data.common_words import COMMON_WORDS
from paxman.core.grammar.normalizers import (
    CaseFold,
    CountryNameFold,
    IDNAFold,
    SeparatorFold,
    StripSeparators,
    SymbolFold,
)
from paxman.core.grammar.scan_context import ScanContext

__all__ = [
    "_run_matchers",
    "_run_matchers_with_context",
    "run_matchers",
    "run_matchers_with_context",
]


def _run_matchers(text: str, compiled: Sequence[Any]) -> list[RecognitionMatch[Any]]:
    context = ScanContext.of(text)
    return _run_matchers_with_context(context, compiled)


def run_matchers(text: str, compiled: Sequence[Any]) -> list[RecognitionMatch[Any]]:
    """Public alias for :func:`_run_matchers` (engine-owned loop)."""
    return _run_matchers(text, compiled)


_VIEW_REGISTRY: dict[str, Any] = {
    "casefolded": CaseFold(),
    "country_normalized": CountryNameFold(),
    "bcp47_normalized": SeparatorFold(),
    "symbol_normalized": SymbolFold(),
    "compact": StripSeparators(),
    "idna": IDNAFold(),
}


def _resolve_view(context: ScanContext, view_name: str | None) -> Any:
    if view_name is None:
        return context.view("__orig__", lambda t: (t, None, None))
    normalizer = _VIEW_REGISTRY.get(view_name)
    if normalizer is not None:
        return context.view(view_name, normalizer.normalize)
    return context.view(view_name, lambda t: (t, None, None))


def _matcher_requires_unsatisfied(matcher: Any, contract: Any | None) -> bool:
    """Return True if matcher's ``requires_features`` is unsatisfied.

    Per ADR §8/§13: matcher omitted when unsatisfied; the registry freezes
    without a contract so contract-dependent omission happens at match time
    (compat shim). If contract is None (e.g. legacy unit tests calling
    run_matchers without contract), we treat all matchers as satisfied.
    """
    requires: frozenset[str] = getattr(matcher, "requires_features", frozenset[str]())
    if not requires:
        return False
    if contract is None:
        return False
    # requires_features: matcher omitted if any required feature falsy/missing
    return any(not bool(getattr(contract, feat, False)) for feat in requires)


def _run_matchers_with_context(
    context: ScanContext,
    compiled: Sequence[Any],
    contract: Any | None = None,
) -> list[RecognitionMatch[Any]]:
    text = context.text
    out: list[RecognitionMatch[Any]] = []
    for grammar in compiled:
        for matcher in getattr(grammar, "matchers", ()):
            # ADR §13 requires_features omission — filter unsatisfied matchers
            if _matcher_requires_unsatisfied(matcher, contract):
                continue
            # T0 anchor prefilter — C-speed skip
            anchors = getattr(matcher, "anchors", None)
            if anchors is not None and not anchors.passes(text, context):
                continue
            # L0 view materialization (lazy, one per ScanContext)
            view_name = getattr(matcher, "view", None)
            if view_name is None:
                view_name = getattr(matcher, "view_name", None)
            view = _resolve_view(context, view_name)
            emit_fn = getattr(matcher, "emit", None)
            if not callable(emit_fn):
                raise TypeError(
                    f"Matcher {type(matcher).__name__} has no callable emit"
                )
            # T1 shape match — kind-specific
            for span in matcher.match(view):
                # Validate span bounds against view subject
                s, e = span
                if not (0 <= s <= e <= len(view.subject)):
                    raise ValueError(
                        f"Matcher {type(matcher).__name__} "
                        f"returned out-of-bounds span {(s, e)} "
                        f"for view {view_name!r} len {len(view.subject)}"
                    )
                o_s, o_e = view.original_span(s, e)
                # IDNAFold trailing \t\n\r: legacy body `[^ <>"...]*` allows
                # tab/LF/CR as body chars and includes trailing ones
                # (e.g. 'A:0\n' → 'A:0\n'). The view strips them, so
                # original_span for view 'A:0' is (0,3) not (0,4). Extend
                # to include trailing stripped chars that are allowed.
                if view_name == "idna":
                    while o_e < len(text) and text[o_e] in "\t\n\r":
                        o_e += 1
                # ADR §16 common-word suppression (B1): short-code matchers marked
                # suppressible are skipped when contract requests it and the
                # word-bounded hit is a high-frequency English function word.
                # Provenance-neutral: suppressed recognition never canonicalizes.
                if (
                    contract is not None
                    and bool(getattr(contract, "suppress_common_words", False))
                    and bool(getattr(matcher, "suppressible", False))
                    and text[o_s:o_e].lower() in COMMON_WORDS
                ):
                    continue
                # Boundary check on original for IDNAFold (stripped \t\n\r).
                # Scanner defers for view_name=="idna"; SeparatorFold
                # (BCP47 '_'->'-') keeps view check ('-' not \w, so AA_→AA passes).
                boundary = getattr(matcher, "boundary", None)
                if (
                    view_name == "idna"
                    and boundary is not None
                    and not check_boundary(text, o_s, o_e, boundary)
                ):
                    continue
                # ADR §10 consuming-mode: anchors consumed for advance
                # but never part of emitted span. Lexicon/Scanner already
                # emit inner span; boundary.is_consuming check below
                # ensures no delimiter leak. Legacy IPv6 via
                # BoundaryGuard.ipv6_token remains zero-width.
                # No trimming needed.
                if boundary is not None and getattr(boundary, "is_consuming", False):
                    # No-op for current trie/scanner (they emit inner span). If a future
                    # scanner emits a span including delimiters, trim here:
                    # o_s/o_e already inner per spec.
                    pass
                notation = emit_fn((o_s, o_e), context)
                out.append(
                    RecognitionMatch(
                        notation=notation,
                        start=o_s,
                        end=o_e,
                        raw_text=text[o_s:o_e],
                    )
                )
    return out


def run_matchers_with_context(
    context: ScanContext, compiled: Sequence[Any], contract: Any | None = None
) -> list[RecognitionMatch[Any]]:
    """Public alias for :func:`_run_matchers_with_context`."""
    return _run_matchers_with_context(context, compiled, contract)
