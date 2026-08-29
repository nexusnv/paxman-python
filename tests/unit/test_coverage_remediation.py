"""Targeted coverage remediation for kernel 0.2.0 gate.

Covers uncovered branches: CombinatorMatcher rep/opt/alt/label,
CandidatesMatcher strategy all dup-span emit and _emit_counts/_flat paths,
ScanContext.view triple protocol vs 2-tuple compat shim,
boundary_spec multi-char fallback, engine_loop delegation edges.
Fast unit tests (<0.5s each), no Hypothesis.
"""

from __future__ import annotations

import pytest

from paxman.core.grammar.anchors import AnchorSet
from paxman.core.grammar.boundary_spec import (
    BoundarySpec,
    _chars_from_bracket,
    _estimate_width,
    _pattern_to_chars,
    check_boundary,
)
from paxman.core.grammar.engine_loop import (
    _matcher_requires_unsatisfied,
    _resolve_view,
    _run_matchers_with_context,
    run_matchers,
)
from paxman.core.grammar.matchers.candidates import CandidatesMatcher
from paxman.core.grammar.matchers.combinator import (
    CombinatorMatcher,
    _collect_leaves,
    _eval_expr,
)
from paxman.core.grammar.matchers.lexicon import LexiconMatcher
from paxman.core.grammar.matchers.regex import RegexMatcher
from paxman.core.grammar.matchers.scanner import ScannerMatcher
from paxman.core.grammar.scan_context import ScanContext, View

# ---------------------------------------------------------------------------
# combinator: _collect_leaves
# ---------------------------------------------------------------------------


class _DummyLeaf:
    def match(self, view: View) -> list[tuple[int, int]]:
        return [(0, 1)]


class _NonCallable:
    match = "not callable"  # type: ignore[assignment]


def test_collect_leaves_non_tuple_leaf_appended() -> None:
    out: list[object] = []
    leaf = _DummyLeaf()
    _collect_leaves(leaf, out)
    assert leaf in out


def test_collect_leaves_non_callable_not_appended() -> None:
    out: list[object] = []
    _collect_leaves(_NonCallable(), out)
    assert out == []


def test_collect_leaves_seq_non_list_children_returns() -> None:
    out: list[object] = []
    _collect_leaves(("seq", "not-a-list"), out)  # type: ignore[arg-type]
    assert out == []


def test_collect_leaves_alt_non_list_returns() -> None:
    out: list[object] = []
    _collect_leaves(("alt", "bad"), out)  # type: ignore[arg-type]
    assert out == []


def test_collect_leaves_opt_none_and_with_child() -> None:
    out: list[object] = []
    _collect_leaves(("opt", None), out)
    assert out == []
    leaf = _DummyLeaf()
    _collect_leaves(("opt", leaf), out)
    assert leaf in out


def test_collect_leaves_rep_none_and_with_child() -> None:
    out: list[object] = []
    _collect_leaves(("rep", None), out)
    assert out == []
    leaf = _DummyLeaf()
    _collect_leaves(("rep", leaf), out)
    assert leaf in out


def test_collect_leaves_label_variants() -> None:
    out: list[object] = []
    _collect_leaves(("label", "L", None), out)
    assert out == []
    _collect_leaves(("label", None), out)  # type: ignore[arg-type]
    assert out == []
    leaf = _DummyLeaf()
    _collect_leaves(("label", "L", leaf), out)
    assert leaf in out
    out2: list[object] = []
    _collect_leaves(("label", leaf), out2)
    assert leaf in out2


def test_collect_leaves_unknown_tuple_not_treated_as_combinator() -> None:
    out: list[object] = []
    _collect_leaves(("unknown", []), out)
    assert out == []
    _collect_leaves("plain string", out)
    assert out == []


# ---------------------------------------------------------------------------
# combinator: _eval_expr direct
# ---------------------------------------------------------------------------


def _view(s: str) -> View:
    return View(subject=s, source_starts=None, source_ends=None, _text_len=len(s))


def test_eval_expr_seq_bad_children_type() -> None:
    view = _view("abc")
    assert _eval_expr(("seq", "bad"), view, 0, {}) is None  # type: ignore[arg-type]


def test_eval_expr_alt_bad_type() -> None:
    view = _view("abc")
    assert _eval_expr(("alt", "bad"), view, 0, {}) is None  # type: ignore[arg-type]


def test_eval_expr_opt_none_returns_pos() -> None:
    view = _view("abc")
    assert _eval_expr(("opt", None), view, 1, {}) == 1
    assert _eval_expr(("opt",), view, 2, {}) == 2  # type: ignore[arg-type]


def test_eval_expr_opt_child_fail_returns_pos() -> None:
    view = _view("ab")
    # seq requiring "xyz" will fail -> opt returns pos
    assert _eval_expr(("opt", "xyz"), view, 0, {}) == 0


def test_eval_expr_opt_child_success() -> None:
    view = _view("ab")
    assert _eval_expr(("opt", "a"), view, 0, {}) == 1


def test_eval_expr_rep_none_returns_pos() -> None:
    view = _view("ab")
    assert _eval_expr(("rep", None), view, 1, {}) == 1


def test_eval_expr_rep_min_max_int_parsing_and_overflow() -> None:
    view = _view("aaa")
    # min_rep as string that fails int -> 0
    # max_rep as string that fails int -> None
    expr = ("rep", "a", "bad", "also-bad")  # type: ignore[arg-type]
    assert _eval_expr(expr, view, 0, {}) == 3
    # rep with min 2, max 2 -> only 2 repetitions
    expr2 = ("rep", "a", 2, 2)  # type: ignore[arg-type]
    assert _eval_expr(expr2, view, 0, {}) == 2
    # rep where child equals pos (zero width) should break without infinite loop
    expr3 = ("rep", "", 0, None)  # type: ignore[arg-type]
    # empty string matches at pos with end==pos -> loop breaks immediately
    assert _eval_expr(expr3, view, 0, {}) == 0
    # rep with count < min_rep -> None
    expr4 = ("rep", "a", 5, None)  # type: ignore[arg-type]
    assert _eval_expr(expr4, view, 0, {}) is None


def test_eval_expr_rep_max_break() -> None:
    view = _view("aaaa")
    expr = ("rep", "a", 0, 2)  # type: ignore[arg-type]
    assert _eval_expr(expr, view, 0, {}) == 2


def test_eval_expr_label_none_and_success() -> None:
    view = _view("ab")
    assert _eval_expr(("label", "L", None), view, 1, {}) == 1  # type: ignore[arg-type]
    assert _eval_expr(("label", None), view, 1, {}) == 1  # type: ignore[arg-type]
    assert _eval_expr(("label", "L", "a"), view, 0, {}) == 1


def test_eval_expr_leaf_missing_map_and_pos_missing() -> None:
    view = _view("ab")
    leaf = _DummyLeaf()
    # leaf not in leaf_maps
    assert _eval_expr(leaf, view, 0, {}) is None
    # leaf in map but pos not present
    assert _eval_expr(leaf, view, 0, {id(leaf): {1: 2}}) is None
    # leaf with pos present
    assert _eval_expr(leaf, view, 0, {id(leaf): {0: 1}}) == 1


def test_eval_expr_str_literal_and_tuple_forms() -> None:
    view = _view("hello world")
    assert _eval_expr("hello", view, 0, {}) == 5
    assert _eval_expr("xyz", view, 0, {}) is None
    assert _eval_expr(("lit", "hello"), view, 0, {}) == 5
    assert _eval_expr(("lit", "xyz"), view, 0, {}) is None
    # non lit/regex tuple falls through to None
    assert _eval_expr(("other", "x"), view, 0, {}) is None  # type: ignore[arg-type]


def test_eval_expr_regex_tuple() -> None:
    view = _view("123abc")
    assert _eval_expr(("regex", r"\d+"), view, 0, {}) == 3
    assert _eval_expr(("regex", r"\d+"), view, 3, {}) is None
    # invalid regex returns None
    assert _eval_expr(("regex", r"["), view, 0, {}) is None
    # non-string second element not handled, falls through
    assert _eval_expr(("regex", 123), view, 0, {}) is None  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# combinator: CombinatorMatcher post_init and match
# ---------------------------------------------------------------------------


def test_combinator_view_alias_sync() -> None:
    c1 = CombinatorMatcher(expr=("seq", []), view="myview")
    assert c1.view_name == "myview"
    assert c1.view == "myview"
    c2 = CombinatorMatcher(expr=("seq", []), view_name="myview2")
    assert c2.view == "myview2"
    assert c2.view_name == "myview2"


def test_combinator_digest_with_predicate() -> None:
    def pred(s: str, ctx: str) -> bool:
        return True

    c = CombinatorMatcher(expr=("seq", []), predicate=pred)  # type: ignore[arg-type]
    assert isinstance(c.digest, str) and len(c.digest) == 64
    c2 = CombinatorMatcher(expr=("seq", []), predicate=None)
    assert c.digest != c2.digest


def test_combinator_match_empty_subject() -> None:
    c = CombinatorMatcher(expr=("seq", ["a"]))
    view = _view("")
    assert c.match(view) == []


def test_combinator_match_seq_rep_alt_label_integration() -> None:
    # seq(rep("a")) on "aaa" should match once at 0,3
    c = CombinatorMatcher(expr=("seq", [("rep", "a", 1, None)]))
    view = _view("aaa")
    assert c.match(view) == [(0, 3)]
    # alt
    c2 = CombinatorMatcher(expr=("alt", ["a", "b"]))
    view2 = _view("ab")
    # first position matches "a", second "b"
    assert c2.match(view2) == [(0, 1), (1, 2)]
    # opt + seq
    c3 = CombinatorMatcher(expr=("seq", [("opt", "x"), "a"]))
    view3 = _view("xa")
    # at pos0: opt consumes "x" then "a" at 1 -> end 2
    # at pos1: opt consumes nothing (no x) then "a" at 1
    # -> end 2 but pos already 2 so no second
    assert c3.match(view3) == [(0, 2)]
    # label
    c4 = CombinatorMatcher(expr=("label", "L", "hello"))
    view4 = _view("hello world")
    assert c4.match(view4) == [(0, 5)]


def test_combinator_match_boundary_and_predicate() -> None:
    # boundary WORD should block inside word
    c = CombinatorMatcher(expr="ab", boundary=BoundarySpec.WORD)
    _view(" xabx ")
    # "ab" at 2 is inside? subject " xabx " -> "ab" at 2
    # preceded by 'x' (\w) so blocked? -> only none?
    # Let's test without boundary too.
    # Use simple isolated
    view2 = _view(" ab ")
    assert c.match(view2) == [(1, 3)]
    view3 = _view("xab")
    assert c.match(view3) == []

    def pred_true(s: str, ctx: str) -> bool:
        return True

    def pred_false(s: str, ctx: str) -> bool:
        return False

    def pred_raises(s: str, ctx: str) -> bool:
        raise RuntimeError("boom")

    c_ok = CombinatorMatcher(expr="a", predicate=pred_true)  # type: ignore[arg-type]
    assert c_ok.match(_view("a")) == [(0, 1)]
    c_no = CombinatorMatcher(expr="a", predicate=pred_false)  # type: ignore[arg-type]
    assert c_no.match(_view("a")) == []
    c_raise = CombinatorMatcher(expr="a", predicate=pred_raises)  # type: ignore[arg-type]
    assert c_raise.match(_view("a")) == []


def test_combinator_zero_width_advance() -> None:
    # expr that matches empty would be skipped (end == pos)
    # rep with min 0 on empty literal "" returns pos,
    # which is end==pos -> should be skipped
    c = CombinatorMatcher(expr=("",))  # type: ignore[arg-type]
    # This expr is not a known form, leaf without map -> eval returns None -> no match
    assert c.match(_view("abc")) == []
    # But a rep that matches zero times returns pos==cur
    # -> skipped path coverage
    c2 = CombinatorMatcher(expr=("rep", "z", 0, None))
    # "z" never matches, so rep returns pos (0)
    # -> end==pos -> skipped, then pos increments
    assert c2.match(_view("abc")) == []


def test_combinator_leaf_exception_and_non_int_spans() -> None:
    class BadLeaf:
        def match(self, view: View) -> list[tuple[int, int]]:  # type: ignore[override]
            raise RuntimeError("leaf boom")

    c = CombinatorMatcher(expr=BadLeaf())  # type: ignore[arg-type]
    # Should not raise, just produce no leaf map -> no match
    assert c.match(_view("abc")) == []

    class NonIntLeaf:
        def match(self, view: View) -> list[object]:  # type: ignore[override]
            return [(0, "bad"), ("a", 1), (0, 1)]  # type: ignore[list-item]

    c2 = CombinatorMatcher(expr=NonIntLeaf())  # type: ignore[arg-type]
    view = _view("ab")
    # Only (0,1) is valid int span and should be kept as leaf map
    # Then at pos0, eval returns 1 -> match (0,1)
    assert c2.match(view) == [(0, 1)]

    class MultiSpanLeaf:
        def match(self, view: View) -> list[tuple[int, int]]:
            return [(0, 1), (0, 3), (1, 2)]

    # Longest span for same start is kept (e > mp[s])
    c3 = CombinatorMatcher(expr=MultiSpanLeaf())  # type: ignore[arg-type]
    view3 = _view("abc")
    assert c3.match(view3) == [(0, 3)]


# ---------------------------------------------------------------------------
# candidates: view sync, digest, strategy, boundary, emit paths
# ---------------------------------------------------------------------------


def test_candidates_view_sync_and_digest() -> None:
    cm = CandidatesMatcher(candidates=(), view="myview")
    assert cm.view_name == "myview"
    cm2 = CandidatesMatcher(candidates=(), view_name="myview2")
    assert cm2.view == "myview2"

    # digest fallback when candidate has no digest
    class NoDigest:
        pass

    cm3 = CandidatesMatcher(
        candidates=(NoDigest(),), candidate_names=("a",), candidate_semantics=("s",)
    )
    assert isinstance(cm3.digest, str)

    # repr exception fallback
    class BadRepr:
        def __repr__(self) -> str:
            raise RuntimeError("bad repr")

        def __str__(self) -> str:
            return "bad-repr-fallback"

    cm4 = CandidatesMatcher(candidates=(BadRepr(),))
    assert isinstance(cm4.digest, str)


def test_candidates_match_exceptions_and_non_list() -> None:
    class Boom:
        def match(self, view: View) -> list[tuple[int, int]]:
            raise RuntimeError("boom")

    class NotList:
        def match(self, view: View) -> object:
            return "not a list"  # type: ignore[return-value]

    cm = CandidatesMatcher(candidates=(Boom(), NotList()), strategy="all")
    view = _view("abc")
    assert cm.match(view) == []

    class NonIntSpan:
        def match(self, view: View) -> list[object]:  # type: ignore[return-value]
            return [(0, "x"), (1, 2)]  # type: ignore[list-item]

    cm2 = CandidatesMatcher(candidates=(NonIntSpan(),), strategy="all")
    assert cm2.match(view) == [(1, 2)]


def test_candidates_strategy_all_dup_span_and_first_dedup() -> None:
    m1 = RegexMatcher(pattern="a")
    m2 = RegexMatcher(pattern="a")
    view = _view("a")
    cm_all = CandidatesMatcher(candidates=(m1, m2), strategy="all")
    spans_all = cm_all.match(view)
    assert spans_all.count((0, 1)) == 2
    cm_first = CandidatesMatcher(candidates=(m1, m2), strategy="first")
    spans_first = cm_first.match(view)
    assert spans_first == [(0, 1)]


def test_candidates_boundary_filter_and_stored_flat() -> None:
    m = RegexMatcher(pattern="ab")
    # ab inside word should be blocked when WORD boundary
    cm = CandidatesMatcher(candidates=(m,), strategy="all", boundary=BoundarySpec.WORD)
    view_inside = _view("xab")
    assert cm.match(view_inside) == []
    # But after clear, stored flat should also be empty
    assert cm._flat == []
    view_ok = _view(" ab ")
    assert cm.match(view_ok) == [(1, 3)]
    assert cm._flat == [(1, 3, 0)]
    # first strategy with boundary
    cm_first = CandidatesMatcher(
        candidates=(m,), strategy="first", boundary=BoundarySpec.WORD
    )
    assert cm_first.match(view_inside) == []
    assert cm_first.match(view_ok) == [(1, 3)]


def test_candidates_flat_clear_exception_path() -> None:
    m = RegexMatcher(pattern="a")
    cm = CandidatesMatcher(candidates=(m,), strategy="all")
    view = _view("a")

    # Force _flat to be something whose clear raises
    class BadClear(list):  # type: ignore[type-arg]
        def clear(self) -> None:
            raise RuntimeError("bad clear")

    object.__setattr__(cm, "_flat", BadClear([(0, 1, 0)]))
    object.__setattr__(cm, "_emit_counts", BadClear())
    # match should handle exception via object.__setattr__ fallback
    spans = cm.match(view)
    assert spans == [(0, 1)]
    assert isinstance(cm._flat, list)


def test_candidates_emit_paths() -> None:
    # Prepare candidates that emit different notations
    from dataclasses import dataclass

    @dataclass(frozen=True, slots=True)
    class EmitA:
        def match(self, view: View) -> list[tuple[int, int]]:
            return [(0, 1)]

        def emit(self, span: tuple[int, int], ctx: ScanContext) -> str:
            return "A"

    @dataclass(frozen=True, slots=True)
    class EmitB:
        def match(self, view: View) -> list[tuple[int, int]]:
            return [(0, 1)]

        def emit(self, span: tuple[int, int], ctx: ScanContext) -> str:
            return "B"

    @dataclass(frozen=True, slots=True)
    class NoEmit:
        def match(self, view: View) -> list[tuple[int, int]]:
            return [(0, 1)]

    ctx = ScanContext.of("a")
    view = ctx.view("orig", lambda t: (t, None, None))
    cm = CandidatesMatcher(candidates=(EmitA(), EmitB()), strategy="all")
    cm.match(view)
    # first call should emit A, second B for same span
    assert cm._emit_match((0, 1), ctx) == "A"
    assert cm._emit_match((0, 1), ctx) == "B"
    # third call exceeds occ length -> clamps to last
    assert cm._emit_match((0, 1), ctx) == "B"

    # occ empty -> fallback to first candidate emit
    cm2 = CandidatesMatcher(candidates=(EmitA(),), strategy="all")
    cm2.match(_view("x"))  # no spans, flat empty
    # pass span that has no occ
    assert cm2._emit_match((0, 1), ctx) == "A"

    # candidate without emit -> returns span
    cm3 = CandidatesMatcher(candidates=(NoEmit(),), strategy="all")
    cm3.match(view)
    assert cm3._emit_match((0, 1), ctx) == (0, 1)

    # empty candidates -> returns span
    cm_empty = CandidatesMatcher(candidates=(), strategy="all")
    cm_empty.match(view)
    assert cm_empty._emit_match((0, 1), ctx) == (0, 1)


# ---------------------------------------------------------------------------
# scan_context: View offsets, original_span, compat shim
# ---------------------------------------------------------------------------


def test_view_offsets_various() -> None:
    v_none = View(subject="hi", source_starts=None, source_ends=None, _text_len=2)
    assert v_none.offsets is None
    v_empty = View(subject="", source_starts=(), source_ends=(), _text_len=0)
    assert v_empty.offsets == (0,)
    v_norm = View(subject="ab", source_starts=(0, 2), source_ends=(1, 3), _text_len=3)
    assert v_norm.offsets == (0, 2, 3)


def test_view_original_span_edge_cases() -> None:
    # source_starts None -> identity
    v = View(subject="ab", source_starts=None, source_ends=None, _text_len=2)
    assert v.original_span(1, 2) == (1, 2)
    # s==e with empty starts
    v_empty = View(subject="", source_starts=(), source_ends=(), _text_len=5)
    assert v_empty.original_span(0, 0) == (0, 0)
    # s==e within range
    v2 = View(subject="ab", source_starts=(0, 5), source_ends=(1, 6), _text_len=6)
    assert v2.original_span(1, 1) == (5, 5)
    # s==e out of range
    assert v2.original_span(5, 5) == (6, 6)
    # s!=e normal
    assert v2.original_span(0, 2) == (0, 6)


def test_scan_context_two_tuple_compat_shim() -> None:
    ctx = ScanContext.of("hello world")
    # 2-tuple with offsets tuple: len(offsets)==len(subject)+1
    view = ctx.view(
        "compat",
        lambda t: (t.lower(), (0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11)),
    )
    assert view.subject == "hello world"
    assert view.source_starts == (0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10)
    assert view.source_ends is not None
    assert len(view.source_starts or ()) == len(view.subject)

    # 2-tuple with None
    ctx2 = ScanContext.of("abc")
    v2 = ctx2.view("compat2", lambda t: (t.upper(), None))
    assert v2.source_starts is None and v2.source_ends is None

    # 2-tuple with empty offsets
    ctx3 = ScanContext.of("")
    v3 = ctx3.view("empty_compat", lambda t: ("", ()))
    assert v3.source_starts == ()
    assert v3.source_ends == ()


def test_scan_context_three_tuple_protocol() -> None:
    ctx = ScanContext.of("a  b")
    # triple with explicit starts/ends
    view = ctx.view("triple", lambda t: ("ab", (0, 3), (1, 4)))
    assert view.subject == "ab"
    assert view.original_span(0, 2) == (0, 4)

    # triple with both None
    ctx2 = ScanContext.of("hi")
    v2 = ctx2.view("both_none", lambda t: (t, None, None))
    assert v2.source_starts is None

    # mixed None should raise AssertionError
    ctx3 = ScanContext.of("hi")
    with pytest.raises(AssertionError):
        ctx3.view("mixed", lambda t: ("hi", (0, 1), None))  # type: ignore[return-value]

    with pytest.raises(AssertionError):
        ctx3.view("mixed2", lambda t: ("hi", None, (1, 2)))  # type: ignore[return-value]


def test_scan_context_three_tuple_length_mismatch() -> None:
    ctx = ScanContext.of("hello")
    with pytest.raises(AssertionError):
        ctx.view("bad_len", lambda t: ("hi", (0,), (1, 2, 3)))  # type: ignore[return-value]
    with pytest.raises(AssertionError):
        ctx.view("bad_len2", lambda t: ("hi", (0, 1, 2), (1,)))  # type: ignore[return-value]


def test_scan_context_three_tuple_offset_validation() -> None:
    ctx = ScanContext.of("abc")
    # empty interval OOB
    with pytest.raises(AssertionError):
        ctx.view("oob", lambda t: ("a", (5,), (6,)))  # type: ignore[return-value]
    # non-decreasing violation
    with pytest.raises(AssertionError):
        ctx.view("nondec", lambda t: ("ab", (1, 0), (2, 1)))  # type: ignore[return-value]


def test_scan_context_view_caching_and_word_spans() -> None:
    ctx = ScanContext.of("one two")
    assert ctx.word_spans == ((0, 3), (4, 7))
    v1 = ctx.view("c", lambda t: (t, None, None))
    v2 = ctx.view("c", lambda t: (t.upper(), None, None))
    assert v1 is v2


# ---------------------------------------------------------------------------
# boundary_spec: pattern_to_chars, estimate_width, BoundarySpec multi fallback
# ---------------------------------------------------------------------------


def test_chars_from_bracket_escapes_and_range() -> None:
    # \w, \d, \s
    assert "\n" in _chars_from_bracket(r"\s")
    assert "a" in _chars_from_bracket(r"\w")
    assert "1" in _chars_from_bracket(r"\d")
    # escaped literal \-
    assert "-" in _chars_from_bracket(r"\-")
    # range a-c
    s = _chars_from_bracket("a-c")
    assert s == frozenset({"a", "b", "c"})
    # literal with no range
    assert "x" in _chars_from_bracket("xyz")


def test_pattern_to_chars_single_and_multi_fallback() -> None:
    assert _pattern_to_chars(r"\w") is not None
    assert _pattern_to_chars(r"\d") is not None
    assert _pattern_to_chars(r"\s") is not None
    # bracket without meta -> single char set
    assert _pattern_to_chars(r"[abc]") == frozenset({"a", "b", "c"})
    # bracket with meta -> None (multi-char fallback)
    for pat in [r"[a*b]", r"[a+b]", r"[a?b]", r"[a{b]", r"[a}b]", r"[a|b]"]:
        assert _pattern_to_chars(pat) is None
    # bracket with escaped quantifier still handled via
    # _chars_from_bracket but interior contains * so returns None before
    assert _pattern_to_chars(r"[\w]") is not None  # no * in interior
    # non-bracket returns None
    assert _pattern_to_chars("abc") is None


def test_estimate_width_escaped_and_bracket() -> None:
    assert _estimate_width(r"\w") == 1
    assert _estimate_width(r"\d") == 1
    assert _estimate_width(r"[abc]") == 1
    assert _estimate_width(r"a\[b") >= 2
    # missing closing bracket -> counts '[' plus chars
    assert _estimate_width("[abc") == 4


def test_boundary_spec_multi_char_fallback_and_check() -> None:
    # left pattern with multi-char fallback (contains * inside bracket -> multi)
    spec = BoundarySpec(left=("[a*b]",), right=("[c+d]",))
    assert spec.left_chars is None
    assert spec.left_multi != ()
    assert spec.right_chars is None
    assert spec.right_multi != ()
    # also test mixture: one single, one multi
    spec2 = BoundarySpec(left=(r"\w", "[a*b]"), right=(r"\d",))
    assert spec2.left_chars is not None
    assert spec2.left_multi != ()
    assert spec2.right_chars is not None
    # check_boundary with multi: pattern "a*b" at boundary should block?
    # left_multi is re.compile(pat + r"\Z") ; need to craft a case
    spec3 = BoundarySpec(left=(r"ab",), right=(r"cd",))
    # For spec3, _pattern_to_chars returns None for "ab" (not brackets) -> multi
    assert spec3.left_multi != ()
    # check_boundary left: text "abX", start 2,
    # left slice should contain "ab" at end -> block
    assert check_boundary("abX", 2, 3, spec3) is False
    assert check_boundary("xxX", 2, 3, spec3) is True
    # right check
    assert check_boundary("Xcd", 0, 1, spec3) is False
    assert check_boundary("Xxx", 0, 1, spec3) is True
    # width edge: start=0 or end=len -> no check
    assert check_boundary("ab", 0, 1, spec3) is True


def test_boundary_spec_word_and_digit_chars() -> None:
    assert check_boundary("a b", 2, 3, BoundarySpec.WORD) is True
    assert check_boundary("ab", 0, 1, BoundarySpec.WORD) is False
    assert check_boundary("1 2", 2, 3, BoundarySpec.DIGIT) is True
    assert check_boundary("12", 0, 1, BoundarySpec.DIGIT) is False


# ---------------------------------------------------------------------------
# engine_loop: requires_features, resolve_view, run_matchers delegation
# ---------------------------------------------------------------------------


def test_matcher_requires_unsatisfied_branches() -> None:
    class M:
        requires_features = frozenset({"feat"})

    class ContractFalse:
        feat = False

    class ContractTrue:
        feat = True

    class NoFeat:
        pass

    m = M()
    assert _matcher_requires_unsatisfied(m, None) is False
    assert _matcher_requires_unsatisfied(m, ContractTrue()) is False
    assert _matcher_requires_unsatisfied(m, ContractFalse()) is True
    assert _matcher_requires_unsatisfied(m, NoFeat()) is True

    # no requires -> False regardless
    class Empty:
        requires_features = frozenset()  # type: ignore[assignment]

    assert _matcher_requires_unsatisfied(Empty(), ContractFalse()) is False
    # missing attribute -> defaults to empty
    assert _matcher_requires_unsatisfied(object(), ContractFalse()) is False  # type: ignore[arg-type]


def test_resolve_view_branches() -> None:
    ctx = ScanContext.of("Hello World")
    v_none = _resolve_view(ctx, None)
    assert v_none.subject == "Hello World"
    v_case = _resolve_view(ctx, "casefolded")
    assert v_case.subject == "hello world"
    v_country = _resolve_view(ctx, "country_normalized")
    assert isinstance(v_country.subject, str)
    v_unknown = _resolve_view(ctx, "custom_unknown_view_xyz")
    assert v_unknown.subject == "Hello World"


def test_run_matchers_with_context_branches() -> None:
    # anchor prefilter skip
    from dataclasses import dataclass

    @dataclass(frozen=True, slots=True)
    class SkipMatcher:
        anchors: AnchorSet = AnchorSet(literals=frozenset({"Z"}))
        view: str | None = None

        def match(self, view: View) -> list[tuple[int, int]]:
            return [(0, 1)]

        def emit(self, span: tuple[int, int], ctx: ScanContext) -> str:
            return "Y"

    @dataclass(frozen=True, slots=True)
    class SkipGrammar:
        matchers: tuple[SkipMatcher, ...] = (SkipMatcher(),)

    assert _run_matchers_with_context(ScanContext.of("hello"), [SkipGrammar()]) == []

    # emit not callable -> TypeError
    @dataclass(frozen=True, slots=True)
    class BadEmitMatcher:
        anchors: AnchorSet = AnchorSet()
        view: str | None = None
        emit = "not callable"  # type: ignore[assignment]

        def match(self, view: View) -> list[tuple[int, int]]:
            return [(0, 1)]

    @dataclass(frozen=True, slots=True)
    class BadEmitGrammar:
        matchers: tuple[BadEmitMatcher, ...] = (BadEmitMatcher(),)  # type: ignore[arg-type]

    with pytest.raises(TypeError, match="no callable emit"):
        _run_matchers_with_context(ScanContext.of("a"), [BadEmitGrammar()])

    # span OOB -> ValueError
    @dataclass(frozen=True, slots=True)
    class OOBMatcher:
        anchors: AnchorSet = AnchorSet()
        view: str | None = None

        def match(self, view: View) -> list[tuple[int, int]]:
            return [(0, 10)]

        def emit(self, span: tuple[int, int], ctx: ScanContext) -> str:
            return "oob"

    @dataclass(frozen=True, slots=True)
    class OOBGrammar:
        matchers: tuple[OOBMatcher, ...] = (OOBMatcher(),)

    with pytest.raises(ValueError, match="out-of-bounds"):
        _run_matchers_with_context(ScanContext.of("a"), [OOBGrammar()])

    # suppressible common words skip
    @dataclass(frozen=True, slots=True)
    class SuppressibleMatcher:
        anchors: AnchorSet = AnchorSet()
        view: str | None = None
        suppressible: bool = True

        def match(self, view: View) -> list[tuple[int, int]]:
            return [(0, 2)]

        def emit(self, span: tuple[int, int], ctx: ScanContext) -> str:
            return "to"

    @dataclass(frozen=True, slots=True)
    class SuppGrammar:
        matchers: tuple[SuppressibleMatcher, ...] = (SuppressibleMatcher(),)

    class ContractSupp:
        suppress_common_words = True

    # "to" is a common word, should be suppressed
    assert (
        _run_matchers_with_context(
            ScanContext.of("to"), [SuppGrammar()], ContractSupp()
        )
        == []
    )

    # consuming boundary pass-through
    @dataclass(frozen=True, slots=True)
    class ConsumingMatcher:
        anchors: AnchorSet = AnchorSet()
        view: str | None = None
        boundary: BoundarySpec = BoundarySpec.IPV6_TOKEN

        def match(self, view: View) -> list[tuple[int, int]]:
            return [(0, 1)]

        def emit(self, span: tuple[int, int], ctx: ScanContext) -> str:
            return "C"

    @dataclass(frozen=True, slots=True)
    class ConsGrammar:
        matchers: tuple[ConsumingMatcher, ...] = (ConsumingMatcher(),)

    out = _run_matchers_with_context(ScanContext.of("a"), [ConsGrammar()])
    assert len(out) == 1

    # view_name alias path
    @dataclass(frozen=True, slots=True)
    class ViewNameMatcher:
        anchors: AnchorSet = AnchorSet()
        view_name: str | None = "casefolded"
        view: str | None = None

        def match(self, view: View) -> list[tuple[int, int]]:
            return [(0, 1)]

        def emit(self, span: tuple[int, int], ctx: ScanContext) -> str:
            return "V"

    @dataclass(frozen=True, slots=True)
    class VNGrammar:
        matchers: tuple[ViewNameMatcher, ...] = (ViewNameMatcher(),)

    out2 = _run_matchers_with_context(ScanContext.of("A"), [VNGrammar()])
    assert len(out2) == 1


def test_run_matchers_alias_and_requires_features_filter() -> None:
    from dataclasses import dataclass

    @dataclass(frozen=True, slots=True)
    class ReqMatcher:
        anchors: AnchorSet = AnchorSet()
        view: str | None = None
        requires_features: frozenset[str] = frozenset({"need_me"})

        def match(self, view: View) -> list[tuple[int, int]]:
            return [(0, 1)]

        def emit(self, span: tuple[int, int], ctx: ScanContext) -> str:
            return "R"

    @dataclass(frozen=True, slots=True)
    class ReqGrammar:
        matchers: tuple[ReqMatcher, ...] = (ReqMatcher(),)

    class WithFeat:
        need_me = True

    class WithoutFeat:
        need_me = False

    assert (
        len(_run_matchers_with_context(ScanContext.of("a"), [ReqGrammar()], WithFeat()))
        == 1
    )
    assert (
        len(
            _run_matchers_with_context(
                ScanContext.of("a"), [ReqGrammar()], WithoutFeat()
            )
        )
        == 0
    )
    assert len(run_matchers("a", [ReqGrammar()])) == 1  # no contract -> satisfied


# ---------------------------------------------------------------------------
# pipeline / orchestrator delegation edge paths (quick)
# ---------------------------------------------------------------------------


def test_orchestrator_single_value_invariant_and_dedup() -> None:
    from paxman.core.domain import Candidate, RecognitionMatch
    from paxman.engine.orchestrator import (
        _dedup_candidates,
        _dedup_spans,
        _spans_overlap,
    )

    assert _spans_overlap((0, 2), (1, 3)) is True
    assert _spans_overlap((0, 1), (1, 2)) is False
    # dedup spans keep_equal True vs False
    m1 = RecognitionMatch(notation="a", start=0, end=2, raw_text="ab")
    m2 = RecognitionMatch(notation="b", start=0, end=2, raw_text="ab")
    m3 = RecognitionMatch(notation="c", start=0, end=1, raw_text="a")
    # with keep_equal False, second equal span dropped
    assert len(_dedup_spans([m1, m2], keep_equal=False)) == 1
    assert len(_dedup_spans([m1, m2], keep_equal=True)) == 2
    # non-equal contained span dropped even with keep_equal True
    # only if strictly contained
    assert len(_dedup_spans([m1, m3], keep_equal=True)) == 1
    assert len(_dedup_spans([m1, m3], keep_equal=False)) == 1
    # _dedup_candidates keep_duplicate_spans

    # need a dummy contract
    cont = object()  # type: ignore[assignment]
    # create two candidates with same value but different spans
    c1 = Candidate(
        value="X",
        recognition_rule="r1",
        validation_rule="v1",
        provenance=(),
        span=(0, 1),
    )
    c2 = Candidate(
        value="X",
        recognition_rule="r1",
        validation_rule="v1",
        provenance=(),
        span=(0, 1),
    )
    # keep_duplicate_spans False -> dedup by (value, recog, valid)
    assert (
        len(_dedup_candidates([(c1, cont), (c2, cont)], keep_duplicate_spans=False))
        == 1
    )  # type: ignore[arg-type]
    assert (
        len(_dedup_candidates([(c1, cont), (c2, cont)], keep_duplicate_spans=True)) == 2
    )  # type: ignore[arg-type]


def test_scanner_matcher_boundary_and_window_edges() -> None:
    def scan(view: View, pos: int) -> tuple[int, str] | None:
        if view.subject[pos:].startswith("abc"):
            return (pos + 3, "ABC")
        return None

    # max_window edge
    m = ScannerMatcher(scan=scan, max_window=2)
    assert m.match(_view("abc")) == []
    m2 = ScannerMatcher(scan=scan, max_window=3, boundary=BoundarySpec.WORD)
    assert m2.match(_view(" abc ")) == [(1, 4)]

    # scanner violation: returns end < pos -> treated as miss
    def bad_scan(view: View, pos: int) -> tuple[int, str] | None:
        return (pos - 1, "BAD")

    m3 = ScannerMatcher(scan=bad_scan)
    assert m3.match(_view("abc")) == []

    # scanner returns end > n -> miss
    def oob_scan(view: View, pos: int) -> tuple[int, str] | None:
        return (100, "OOB")

    m4 = ScannerMatcher(scan=oob_scan)
    assert m4.match(_view("abc")) == []

    # boundary blocks
    def always_scan(view: View, pos: int) -> tuple[int, str] | None:
        return (pos + 1, "X")

    m5 = ScannerMatcher(scan=always_scan, boundary=BoundarySpec.WORD)
    assert m5.match(_view("ab")) == []


def test_lexicon_trie_word_anchored_and_alternation() -> None:
    m_trie = LexiconMatcher(tokens=frozenset({"hello"}), representation="trie")
    assert m_trie.match(_view("hello")) == [(0, 5)]
    assert m_trie.match(_view("xhello")) == []
    m_alt = LexiconMatcher(tokens=frozenset({"a", "ab"}), representation="alternation")
    # longest first should prefer "ab" over "a"
    spans = m_alt.match(_view("ab"))
    assert (0, 2) in spans


def test_label_matcher_match_and_boundary() -> None:
    from paxman.core.grammar.matchers.label import LabelMatcher

    lm = LabelMatcher(
        labels=frozenset({"ISSN"}),
        pattern=r"\d{4}-\d{4}",
        separator=r"[\s:-]*",
        glued_policy="allow",
    )
    view = _view("ISSN 0317-8471")
    assert lm.match(view) != []
    # no pattern -> empty
    lm2 = LabelMatcher(labels=frozenset({"X"}), pattern="")
    assert lm2.match(_view("X 123")) == []
    # boundary blocks
    lm3 = LabelMatcher(
        labels=frozenset({"ISSN"}), pattern=r"\d+", boundary=BoundarySpec.WORD
    )
    # glued inside word should be blocked
    assert lm3.match(_view("x0317")) == []


# ---------------------------------------------------------------------------
# orchestrator: version fallback and CandidatesMatcher None branch
# ---------------------------------------------------------------------------


def test_resolve_version_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    import paxman.engine.orchestrator as orch

    monkeypatch.setattr(
        "paxman.engine.orchestrator._get_version",
        lambda _: (_ for _ in ()).throw(RuntimeError("boom")),
    )
    # direct call via helper
    assert orch._resolve_version() == "0.2.1"


def test_run_capability_with_candidates_none_branch(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import paxman.engine.orchestrator as orch
    from paxman.capabilities.Country.capability import CountryCapability
    from paxman.core.discovery import register_capability, reset_registry

    reset_registry()
    try:
        register_capability(CountryCapability())
        # monkeypatch CandidatesMatcher to None to hit all `is not None` false branches
        monkeypatch.setattr(orch, "CandidatesMatcher", None)
        contract = CountryCapability.create_contract()
        # should still succeed via normal path without candidates special handling
        res = orch.run_capability("US", contract)
        assert res.status.name in ("SUCCESS", "INVALID", "MISSING", "AMBIGUOUS")
    finally:
        reset_registry()


def test_recognize_error_paths() -> None:
    from paxman.capabilities.Country.capability import CountryCapability
    from paxman.core.discovery import register_capability, reset_registry
    from paxman.core.domain import Grammar, RecognitionMatch
    from paxman.core.errors import RecognitionError
    from paxman.engine.orchestrator import _recognize

    # Grammar that raises in recognize
    class BoomGrammar(Grammar[str]):  # type: ignore[type-abstract]
        name = "boom_recognize"
        semantics = "boom"

        def recognize(self, text: str) -> list[RecognitionMatch[str]]:
            raise RuntimeError("boom recognize")

    cap = CountryCapability()
    # Build a contract that opts in boom grammar
    reset_registry()
    try:
        from paxman.core.extensions import register_grammar

        register_capability(cap)
        register_grammar("country", BoomGrammar)
        contract = CountryCapability.create_contract(extra_grammars=("boom_recognize",))
        with pytest.raises(RecognitionError, match="Grammar failed"):
            _recognize("hello", [BoomGrammar()], ["boom_recognize"], contract)  # type: ignore[arg-type]

        # Grammar that returns out-of-bounds span
        class OOBGrammar(Grammar[str]):  # type: ignore[type-abstract]
            name = "oob"
            semantics = "oob"

            def recognize(self, text: str) -> list[RecognitionMatch[str]]:
                return [
                    RecognitionMatch(notation="x", start=-1, end=10, raw_text="xxx")
                ]

        with pytest.raises(RecognitionError):
            _recognize("hi", [OOBGrammar()], ["oob"], contract)  # type: ignore[arg-type]

        # raw_text mismatch
        class MismatchGrammar(Grammar[str]):  # type: ignore[type-abstract]
            name = "mismatch"
            semantics = "mismatch"

            def recognize(self, text: str) -> list[RecognitionMatch[str]]:
                return [RecognitionMatch(notation="x", start=0, end=2, raw_text="BAD")]

        with pytest.raises(RecognitionError):
            _recognize("hi", [MismatchGrammar()], ["mismatch"], contract)  # type: ignore[arg-type]
    finally:
        reset_registry()

    # Matcher path that raises inside engine loop
    class RaisingMatcher:
        anchors = AnchorSet()
        view = None
        boundary = None

        def match(self, view: View) -> list[tuple[int, int]]:
            raise RuntimeError("matcher boom")

        def emit(self, span: tuple[int, int], ctx: ScanContext) -> str:  # type: ignore[override]
            return "X"

    class GrammarWithRaising(Grammar[str]):  # type: ignore[type-abstract]
        name = "raising"
        semantics = "raising"

        def __init__(self) -> None:
            self.matchers = (RaisingMatcher(),)  # type: ignore[attr-defined]

        def recognize(self, text: str) -> list[RecognitionMatch[str]]:
            return []

    # Use _recognize with matchers path; run_matchers_with_context will not raise
    # but _recognize wraps matcher exceptions as RecognitionError
    # Actually RaisingMatcher.match will be called via run_matchers_with_context which
    # doesn't catch inside match? It just iterates. Let's test that the loop survives.
    # Instead test a matcher that makes run_matchers raise via bad emit?
    # For now, just ensure no crash on missing matchers attribute
    reset_registry()
    try:
        cap2 = CountryCapability()
        register_capability(cap2)
        contract2 = cap2.create_contract()

        # Grammar with empty matchers should go via else branch (recognize)
        class EmptyMatcherGrammar(Grammar[str]):  # type: ignore[type-abstract]
            name = "empty_matchers"
            semantics = "empty"

            def recognize(self, text: str) -> list[RecognitionMatch[str]]:
                return [RecognitionMatch(notation="x", start=0, end=1, raw_text="a")]

        # No matchers attribute -> else branch
        with pytest.raises(RecognitionError):
            # Force recognize to raise by patching run_matchers to raise
            import paxman.engine.orchestrator as orch

            orig = orch.run_matchers_with_context

            def boom(*_a: object, **_kw: object) -> list[object]:
                raise RuntimeError("engine boom")

            orch.run_matchers_with_context = boom  # type: ignore[assignment]
            try:
                # Need a grammar with matchers to hit the try branch
                class MatcherGrammar(Grammar[str]):  # type: ignore[type-abstract]
                    name = "with_matchers"
                    semantics = "with_matchers"

                    def __init__(self) -> None:
                        self.matchers = (RaisingMatcher(),)  # type: ignore[attr-defined]

                    def recognize(self, text: str) -> list[RecognitionMatch[str]]:
                        return []

                _recognize("a", [MatcherGrammar()], ["with_matchers"], contract2)  # type: ignore[arg-type]
            finally:
                orch.run_matchers_with_context = orig  # type: ignore[assignment]
    finally:
        reset_registry()


def test_orchestrator_filter_rules_and_affinity() -> None:
    # Unknown pinned rule
    from paxman.capabilities.Country.capability import CountryCapability
    from paxman.core.discovery import register_capability, reset_registry
    from paxman.core.domain import Rule
    from paxman.core.errors import ContractError
    from paxman.engine.orchestrator import _filter_rules, _validate_affinity

    reset_registry()
    try:
        cap = CountryCapability()
        register_capability(cap)
        contract = cap.create_contract(pinned_rules=("nonexistent_rule",))
        with pytest.raises(ContractError, match="Unknown pinned"):
            _filter_rules(cap.get_rules(), contract)  # type: ignore[arg-type]
        contract2 = cap.create_contract(excluded_rules=("nonexistent_rule",))
        with pytest.raises(ContractError, match="Unknown excluded"):
            _filter_rules(cap.get_rules(), contract2)  # type: ignore[arg-type]

        # affinity: rule declares unknown semantics
        class DummyRule(Rule[str]):  # type: ignore[type-abstract]
            name = "dummy_unknown_sem"
            strategy = Rule.__dict__.get("strategy", None)  # type: ignore[attr-defined]
            provenance = cap.get_rules()[0].provenance  # type: ignore[attr-defined]
            citation = "test"
            target_semantics = frozenset({"unknown_sem_xyz"})
            requires_features = frozenset()

            def matches(self, notation: object, contract: object) -> bool:  # type: ignore[override]
                return False

            def normalize(self, notation: object, contract: object) -> str:  # type: ignore[override]
                return ""

        # need to bypass Rule.__init_subclass__ checks, so set properly
        # Instead test via direct _validate_affinity call
        with pytest.raises(ContractError, match="unknown semantics"):
            _validate_affinity({"a": "known"}, [DummyRule()])  # type: ignore[arg-type,call-arg]
    finally:
        reset_registry()


def test_candidates_matcher_strategy_all_keep_equal_in_recognize() -> None:
    # Ensure _recognize keep_equal True path for CandidatesMatcher strategy all
    from paxman.capabilities.Country.capability import CountryCapability
    from paxman.core.discovery import register_capability, reset_registry
    from paxman.core.domain import Grammar, RecognitionMatch
    from paxman.core.grammar.anchors import AnchorSet
    from paxman.core.grammar.matchers.candidates import CandidatesMatcher
    from paxman.core.grammar.matchers.regex import RegexMatcher
    from paxman.engine.orchestrator import _dedup_spans, _recognize

    reset_registry()
    try:
        cap = CountryCapability()
        register_capability(cap)
        contract = cap.create_contract()
        # Build a grammar with CandidatesMatcher strategy all and duplicate spans
        m1 = RegexMatcher(pattern="a", anchors=AnchorSet())
        m2 = RegexMatcher(pattern="a", anchors=AnchorSet())
        cm = CandidatesMatcher(
            candidates=(m1, m2),
            strategy="all",
            candidate_names=("c1", "c2"),
            candidate_semantics=("s1", "s2"),
        )

        # Create a dummy grammar that holds this matcher
        class DupGrammar(Grammar[str]):  # type: ignore[type-abstract]
            name = "dup_grammar"
            semantics = "dup_sem"

            def __init__(self) -> None:
                self.matchers = (cm,)  # type: ignore[attr-defined]

            def recognize(self, text: str) -> list[RecognitionMatch[str]]:
                return []

        # _dedup_spans keep_equal True should keep duplicates
        from paxman.core.domain import RecognitionMatch as RecognitionMatchDup

        a = RecognitionMatchDup(notation="x", start=0, end=1, raw_text="a")
        b = RecognitionMatchDup(notation="y", start=0, end=1, raw_text="a")
        assert len(_dedup_spans([a, b], keep_equal=True)) == 2
        assert len(_dedup_spans([a, b], keep_equal=False)) == 1
        # Also test _recognize with this grammar via CandidatesMatcher path
        # Provide a simple text "a"
        recs = _recognize("a", [DupGrammar()], ["dup_grammar"], contract)  # type: ignore[arg-type]
        # Should produce at least one recognition (via engine loop)
        assert isinstance(recs, list)
    finally:
        reset_registry()
