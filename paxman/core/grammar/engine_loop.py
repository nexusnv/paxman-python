"""Engine-owned match loop L0+L1+L2."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from paxman.core.domain import RecognitionMatch
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

    Per D5: matcher omitted from compiled set at freeze when unsatisfied;
    for the compat shim we filter at match time. If contract is None
    (e.g. legacy unit tests calling run_matchers without contract), we treat
    all matchers as satisfied.
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
            # D5 requires_features omission — filter unsatisfied matchers
            if _matcher_requires_unsatisfied(matcher, contract):
                continue
            # T0 anchor prefilter — C-speed skip
            anchors = getattr(matcher, "anchors", None)
            if anchors is not None and not anchors.passes(text, context):
                continue
            # L0 view materialization (lazy, one per ScanContext)
            view_name = getattr(matcher, "view", None)
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
                # ADR §10 consuming-mode: anchors consumed for advance
                # but never part of emitted span. Lexicon/Scanner already
                # emit inner span; boundary.is_consuming check below
                # ensures no delimiter leak. Legacy IPv6 via
                # BoundaryGuard.ipv6_token remains zero-width.
                # No trimming needed.
                boundary = getattr(matcher, "boundary", None)
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
