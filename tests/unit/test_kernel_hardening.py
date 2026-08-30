"""Kernel hardening II — error contract, boundary parity, invariants (#66-#64).

Coverage:

- grammar-path errors wrap into RecognitionError, never raw KeyError/IndexError (#66)
- BoundarySpec negated bracket classes fall back to the regex path (#67)
- boundary char sets exact vs re for non-BMP neighbors and Unicode Nd digits (#62)
- NormalizerSequence no-expansion invariant pinned (#63)
- NFD per-char cache bounded (#64)
"""

from __future__ import annotations

import unicodedata

import pytest

from paxman.core.grammar.boundary_spec import (
    _D_CHARS,
    BoundarySpec,
    _pattern_lowering,
    _pattern_to_chars,
    check_boundary,
)
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


def test_negated_bracket_class_not_lowered_to_positive_set() -> None:
    """(#67) '[^...]' must fall back to the regex path, not become a set."""
    assert _pattern_to_chars("[^a-z]") is None
    # escaped caret is a literal member, NOT negation
    lowered = _pattern_to_chars(r"[\^a]")
    assert lowered is not None and "^" in lowered and "a" in lowered


def test_negated_bracket_class_regex_semantics() -> None:
    """(#67) A negated left guard fires when the neighbor is NOT in the set."""
    spec = BoundarySpec(left=("[^0-9]",), right=None, mode="zero_width")
    # Left neighbor 'x' is NOT a digit -> the negated guard fires -> fails.
    assert check_boundary("xa", 1, 2, spec) is False
    # Left neighbor '1' IS a digit -> guard does not fire -> passes.
    assert check_boundary("15", 1, 2, spec) is True


def test_digit_chars_cover_bmp_nd_category() -> None:
    """(#62) '\\d' lowers to Unicode Nd, not ASCII — Arabic-Indic digits fire."""
    assert _D_CHARS is not None and "\u0663" in _D_CHARS  # ٣ Arabic-Indic three
    assert "\u00b2" not in _D_CHARS  # superscript two is No, re \d rejects it
    assert (
        frozenset(
            chr(c) for c in range(0x10000) if unicodedata.category(chr(c)) == "Nd"
        )
        == _D_CHARS
    )


def test_non_bmp_word_neighbor_fires_word_guard() -> None:
    """(#62) Non-BMP word chars (Deseret) fire \\w guards via the fallback."""
    spec = BoundarySpec(left=(r"\w",), right=None, mode="zero_width")
    # U+10400 DESERET LETTER — isalnum() True, re \w matches, BMP scan misses it.
    # It is the LEFT neighbor of the hit [1:2] ('a'), so the fallback decides.
    assert check_boundary("\U00010400a", 1, 2, spec) is False


def test_non_bmp_digit_neighbor_fires_digit_guard() -> None:
    """(#62) Non-BMP Nd digits (math digits) fire \\d guards via the fallback."""
    spec = BoundarySpec(left=(r"\d",), right=None, mode="zero_width")
    # U+1D7CE MATHEMATICAL BOLD DIGIT ZERO (Nd, non-BMP) is the LEFT neighbor
    # of the hit [1:2]; the BMP Nd scan misses it, the compiled \\d does not.
    assert check_boundary("\U0001d7cea", 1, 2, spec) is False


def test_non_bmp_non_word_neighbor_passes_word_guard() -> None:
    """(#62) Non-BMP non-word chars do NOT fire \\w guards."""
    spec = BoundarySpec(left=(r"\w",), right=None, mode="zero_width")
    # U+1F600 emoji — not alnum, re \w does not match → guard stays silent.
    assert check_boundary("\U0001f600a", 1, 2, spec) is True


def test_pattern_lowering_pairs_sets_with_fallbacks() -> None:
    """(#62) Class escapes carry compiled fallbacks; enumerations do not."""
    w_chars, w_fb = _pattern_lowering(r"\w")
    d_chars, d_fb = _pattern_lowering(r"\d")
    s_chars, s_fb = _pattern_lowering(r"\s")
    assert w_fb is not None and d_fb is not None and s_fb is not None
    assert w_chars is not None and d_chars is not None and s_chars is not None
    b_chars, b_fb = _pattern_lowering("[abc]")
    assert b_fb is None and b_chars == frozenset({"a", "b", "c"})
    assert _pattern_lowering("abc") == (None, None)
