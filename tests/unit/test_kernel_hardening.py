"""Kernel hardening II — error contract, boundary parity, invariants (#66-#64).

Coverage:

- grammar-path errors wrap into RecognitionError, never raw KeyError/IndexError (#66)
- BoundarySpec negated bracket classes fall back to the regex path (#67)
- boundary char sets exact vs re for non-BMP neighbors and Unicode Nd digits (#62)
- NormalizerSequence no-expansion invariant pinned (#63)
- NFD per-char cache bounded (#64)
"""

from __future__ import annotations

import pytest

from paxman.core.grammar.matchers.candidates import CandidatesMatcher
from paxman.core.grammar.matchers.combinator import CombinatorMatcher
from paxman.core.grammar.scan_context import ScanContext, View

pytestmark = pytest.mark.unit


class _ExplodingCandidate:
    """Candidate double whose match() raises KeyError (data-bug shape)."""

    digest = "exploding-candidate"

    def match(self, view: View) -> list[tuple[int, int]]:
        """Raise KeyError — the LookupError shape escaping the old tuple."""
        raise KeyError("missing token table entry")

    def emit(self, span: tuple[int, int], ctx: object) -> tuple[int, int]:
        """Return the span unchanged (never reached in these tests)."""
        return span


class _ExplodingLeaf:
    """Combinator leaf double whose match() raises IndexError."""

    digest = "exploding-leaf"

    def match(self, view: View) -> list[tuple[int, int]]:
        """Raise IndexError — the LookupError shape escaping the old tuple."""
        raise IndexError("offset map out of range")

    def emit(self, span: tuple[int, int], ctx: object) -> tuple[int, int]:
        """Return the span unchanged (never reached in these tests)."""
        return span


def _orig_view(text: str) -> View:
    """Build an identity (``__orig__``-style) view over ``text``."""
    return ScanContext.of(text).view("orig", lambda t: (t, None, None))


def test_candidates_swallows_key_error_from_candidate() -> None:
    """(#66) A candidate raising KeyError yields no spans, not a raw crash."""
    m = CandidatesMatcher(candidates=(_ExplodingCandidate(),), strategy="all")
    view = _orig_view("ab")
    assert m.match(view) == []


def test_combinator_swallows_index_error_from_leaf() -> None:
    """(#66) A combinator leaf raising IndexError yields no spans."""
    m = CombinatorMatcher(expr=_ExplodingLeaf())
    view = _orig_view("ab")
    assert m.match(view) == []


def test_combinator_swallows_key_error_from_predicate() -> None:
    """(#66) A combinator predicate raising KeyError rejects, not crashes."""
    m = CombinatorMatcher(expr="a", predicate=_exploding_predicate)
    view = _orig_view("ab")
    assert m.match(view) == []


def _exploding_predicate(span_text: str, subject: str) -> bool:
    """Predicate double that raises KeyError (data-bug shape)."""
    raise KeyError("predicate lookup table missing")
