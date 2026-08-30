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
from paxman.core.grammar.normalizers import NormalizerSequence, StripSeparators
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


class _ExpandingNormalizer:
    """Test normalizer violating the no-expansion invariant (1 cur -> 2 nxt).

    Emits unit-width but non-injective offsets: cur[0] is claimed by two nxt
    chars (``starts`` [0, 0]) — exactly the expansion shape composition must
    reject, since each nxt char still spans one cur char.
    """

    name = "expanding"
    provenance = None
    stripped_chars = None

    def normalize(
        self, text: str
    ) -> tuple[str, tuple[int, ...] | None, tuple[int, ...] | None]:
        if not text:
            return "", (), ()
        subject = text[0] + "-" + text[1:]  # 1 cur char -> 2 nxt chars
        starts: list[int] = []
        ends: list[int] = []
        for i, _ch in enumerate(text):
            if i == 0:
                starts.extend([0, 0])  # expansion: two nxt chars from cur[0]
                ends.extend([1, 1])
            else:
                starts.append(i)
                ends.append(i + 1)
        return subject, tuple(starts), tuple(ends)


def test_sequence_composition_rejects_expanding_normalizer() -> None:
    """(#63) Composition asserts the no-expansion invariant — fails fast.

    A single-step sequence would only ASSIGN offsets (``cur_starts is None``
    on entry), so the compose branch needs two offset-returning steps:
    ``StripSeparators`` on "a b" returns offsets (setting ``cur_starts``),
    forcing the expanding step's offsets through composition, where the
    invariant check fires.
    """
    seq = NormalizerSequence(steps=(StripSeparators(), _ExpandingNormalizer()))
    with pytest.raises(ValueError, match="expansion is not supported"):
        seq.normalize("a b")


def test_bracket_word_non_bmp_fallback() -> None:
    """(#62) Positive bracket classes containing \\w need non-BMP fallback."""
    spec = BoundarySpec(left=("[\\w]",), right=None, mode="zero_width")
    # U+10400 DESERET LETTER is word-like but BMP scan is blind to it.
    assert check_boundary("\U00010400a", 1, 2, spec) is False
    # Non-word emoji must not fire the \\w bracket.
    assert check_boundary("\U0001f600a", 1, 2, spec) is True


def test_bracket_digit_non_bmp_fallback() -> None:
    """(#62) Positive bracket classes containing \\d need non-BMP fallback."""
    spec = BoundarySpec(left=("[\\d]",), right=None, mode="zero_width")
    # U+1D7CE MATHEMATICAL BOLD DIGIT is Nd, non-BMP, bracket contains \\d.
    assert check_boundary("\U0001d7cea", 1, 2, spec) is False
    # Deseret is word but not digit — bracket [\\d] must not fire.
    assert check_boundary("\U00010400a", 1, 2, spec) is True


def test_bracket_word_mixed_non_bmp_fallback() -> None:
    """(#62) Brackets like [\\w:.] keep fallback for non-BMP word chars."""
    left_spec = BoundarySpec(left=("[\\w:.]",), right=None, mode="zero_width")
    assert check_boundary("\U00010400a", 1, 2, left_spec) is False
    right_spec = BoundarySpec(left=None, right=("[\\w:.]",), mode="zero_width")
    assert check_boundary("a\U00010400", 0, 1, right_spec) is False  # right neighbor


def test_nfd_char_cache_is_bounded() -> None:
    """(#64) The per-char NFD memo is an lru_cache, not an unbounded dict."""
    from paxman.core.grammar import normalizers

    assert normalizers._nfd_char.cache_info().maxsize == 8192
    # deterministic pure function: same char -> same decomposition
    assert normalizers._nfd_char("é") == normalizers._nfd_char("é")
    assert normalizers._nfd_char("é") == "e\u0301"
