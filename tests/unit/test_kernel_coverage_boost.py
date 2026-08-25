"""Boost coverage for kernel additions."""

from __future__ import annotations

import pytest

from paxman.core.grammar.anchors import AnchorSet
from paxman.core.grammar.boundary_spec import BoundarySpec
from paxman.core.grammar.engine_loop import (
    _run_matchers,
    _run_matchers_with_context,
    run_matchers,
)
from paxman.core.grammar.matchers.candidates import CandidatesMatcher
from paxman.core.grammar.matchers.combinator import CombinatorMatcher
from paxman.core.grammar.matchers.label import LabelMatcher
from paxman.core.grammar.matchers.lexicon import LexiconMatcher, _check_boundary
from paxman.core.grammar.matchers.property import PropertyMatcher
from paxman.core.grammar.normalizers import (
    AccentStrip,
    CaseFold,
    CountryNameFold,
    IDNAFold,
    NormalizerSequence,
    SeparatorFold,
    StripSeparators,
    SymbolFold,
)
from paxman.core.grammar.scan_context import ScanContext, View


def test_property_contains_empty() -> None:
    m = PropertyMatcher(ranges=())
    assert m._contains(65) is False
    assert m.match(View(subject="A", offsets=None, _text_len=1)) == []


def test_property_contains_hit_and_miss() -> None:
    m = PropertyMatcher(ranges=((0x41, 0x5A), (0x61, 0x7A)))
    assert m._contains(0x41) is True
    assert m._contains(0x5A) is True
    assert m._contains(0x42) is True
    assert m._contains(0x60) is False
    assert m._contains(0x61) is True
    assert m._contains(0x20) is False
    assert m._contains(0x7B) is False


def test_property_with_view_name_and_boundary() -> None:
    m = PropertyMatcher(
        ranges=((48, 57),), view_name="orig", boundary=BoundarySpec.DIGIT
    )
    assert m.view_name == "orig"
    assert m.boundary == BoundarySpec.DIGIT


def test_scan_context_offset_invariant_violation() -> None:
    ctx = ScanContext.of("hello world")

    # bad offsets length
    def bad_len(s: str) -> tuple[str, tuple[int, ...] | None]:
        return "hi", (0, 1)  # len 2+1 expected 3 but got 2

    with pytest.raises(AssertionError):
        ctx.view("bad", bad_len)

    # empty interval
    def bad_interval(s: str) -> tuple[str, tuple[int, ...] | None]:
        return "ab", (0, 0, 5)

    ctx2 = ScanContext.of("hello")
    with pytest.raises(AssertionError):
        ctx2.view("bad2", bad_interval)


def test_scan_context_view_caching() -> None:
    ctx = ScanContext.of("hello world")
    v1 = ctx.view("case", lambda t: (t.lower(), None))
    v2 = ctx.view("case", lambda t: (t.upper(), None))
    assert v1 is v2
    assert v1.subject == "hello world"


def test_view_original_span_with_offsets() -> None:
    ctx = ScanContext.of("a  b")
    view = ctx.view("c", lambda t: ("ab", (0, 3, 4)))
    assert view.original_span(0, 2) == (0, 4)
    assert view.original_span(1, 2) == (3, 4)


def test_check_boundary_left_right() -> None:
    assert _check_boundary("x y", 2, 3, BoundarySpec.WORD) is True
    # left char is 'x' which is \w, should block WORD
    assert _check_boundary("x y", 1, 2, BoundarySpec.WORD) is False
    # right check: "a b" span "a" at 0,1 -> suffix " b" starts with " " not \w so passes
    assert _check_boundary("a b", 0, 1, BoundarySpec.WORD) is True
    # blocked right: "ab" span "a" -> next char "b" is \w -> block
    assert _check_boundary("ab", 0, 1, BoundarySpec.WORD) is False
    # degree sign
    assert BoundarySpec.DEGREE_WORD_SIGN.left is not None


def test_normalizer_sequence_offsets() -> None:
    seq = NormalizerSequence(steps=(StripSeparators(), CaseFold()))
    subj, offs = seq.normalize("+1 (555) 123-4567")
    assert subj == "+15551234567"
    assert offs is not None
    seq2 = NormalizerSequence(steps=(CaseFold(), SeparatorFold()))
    subj2, offs2 = seq2.normalize("Hello_World")
    assert subj2 == "hello-world"
    assert seq2.name == "casefolded+normalized"
    assert seq2.provenance is not None


def test_country_name_fold_empty_and_identity() -> None:
    nf = CountryNameFold()
    subj, offs = nf.normalize("")
    assert subj == ""
    assert offs == (0,)
    subj2, offs2 = nf.normalize("hello")
    assert subj2 == "hello"
    assert offs2 is None
    subj3, offs3 = nf.normalize("Côte d'Ivoire")
    assert "cote" in subj3
    subj4, _ = nf.normalize("United\u2013States")
    assert "united states" in subj4


def test_accent_strip_and_symbol_fold() -> None:
    assert AccentStrip().normalize("Côte")[0] == "cote"
    assert SymbolFold().normalize("a²")[0] == "a2"
    assert SeparatorFold().normalize("a_b")[0] == "a-b"
    assert CaseFold().normalize("ABC")[0] == "abc"


def test_idna_fold_tab() -> None:
    nf = IDNAFold()
    subj, offs = nf.normalize("a\tb\nc")
    assert subj == "abc"
    assert offs is not None
    subj2, offs2 = nf.normalize("abc")
    assert offs2 is None


def test_strip_separators_no_change() -> None:
    nf = StripSeparators()
    subj, offs = nf.normalize("15551234567")
    assert offs is None
    subj2, offs2 = nf.normalize("+1-555")
    assert offs2 is not None


def test_lexicon_matcher_alternation_with_boundary() -> None:
    matcher = LexiconMatcher(
        tokens=frozenset({"hello", "world"}),
        boundary=BoundarySpec.WORD,
        representation="alternation",
    )
    ctx = ScanContext.of("hello world")
    view = ctx.view("orig", lambda t: (t, None))
    spans = matcher.match(view)
    assert (0, 5) in spans
    assert (6, 11) in spans
    # inside word should be blocked
    matcher2 = LexiconMatcher(
        tokens=frozenset({"ell"}),
        boundary=BoundarySpec.WORD,
        representation="alternation",
    )
    ctx2 = ScanContext.of("hello")
    view2 = ctx2.view("orig", lambda t: (t, None))
    assert matcher2.match(view2) == []


def test_lexicon_matcher_trie_longest() -> None:
    tokens = frozenset({"a", "ab", "abc", "hello world"})
    # force trie by passing representation trie or >500
    m = LexiconMatcher(tokens=tokens, boundary=None, representation="trie")
    ctx = ScanContext.of("abc hello world")
    view = ctx.view("orig", lambda t: (t, None))
    spans = m.match(view)
    assert (0, 3) in spans  # longest abc
    # hello world spans 4..15?
    assert any(s == 4 and e - s == 11 for s, e in spans)
    # word anchored: inside word not matched
    m2 = LexiconMatcher(tokens=frozenset({"ell"}), representation="trie")
    ctx2 = ScanContext.of("hello")
    view2 = ctx2.view("orig", lambda t: (t, None))
    assert m2.match(view2) == []


def test_lexicon_matcher_trie_boundary() -> None:
    m = LexiconMatcher(
        tokens=frozenset({"hello"}), boundary=BoundarySpec.WORD, representation="trie"
    )
    ctx = ScanContext.of("xhelloy")  # no space -> word anchored no match
    view = ctx.view("orig", lambda t: (t, None))
    assert m.match(view) == []
    # but with spaces it matches
    ctx2 = ScanContext.of(" hello ")
    view2 = ctx2.view("orig", lambda t: (t, None))
    assert m.match(view2) == [(1, 6)]


def test_label_matcher_and_candidates() -> None:
    lm = LabelMatcher(
        labels=frozenset({"IBAN"}), separator=r"[\s:-]+", glued_policy="reject"
    )
    assert lm.matches_prefix("IBAN DE89") is True
    assert lm.matches_prefix("IBANDE89") is False
    lm2 = LabelMatcher(
        labels=frozenset({"ISSN"}), separator=r"[\s:-]*", glued_policy="allow"
    )
    assert lm2.matches_prefix("ISSN03178471") is True
    assert lm2.matches_prefix("ISSN 0317") is True

    cm = CandidatesMatcher(candidates=("a", "b"), strategy="first")
    assert cm.strategy == "first"
    assert cm.match(View(subject="x", offsets=None, _text_len=1)) == []

    cb = CombinatorMatcher(expr=("alt", ["a", "b"]))
    assert cb.match(View(subject="ab", offsets=None, _text_len=2)) == []


def test_engine_loop_with_dummy_matchers() -> None:
    # Build dummy grammar with matchers
    from dataclasses import dataclass

    @dataclass(frozen=True, slots=True)
    class DummyMatcher:
        anchors: AnchorSet
        view: str | None = None

        def match(self, view: View) -> list[tuple[int, int]]:
            return [(0, 1)]

        def emit(self, span: tuple[int, int], ctx: ScanContext) -> str:
            return "X"

    @dataclass(frozen=True, slots=True)
    class DummyGrammar:
        matchers: tuple[DummyMatcher, ...] = (DummyMatcher(anchors=AnchorSet()),)

    ctx = ScanContext.of("a")
    out = _run_matchers_with_context(ctx, [DummyGrammar()])
    assert len(out) == 1
    assert out[0].raw_text == "a"
    assert out[0].notation == "X"
    out2 = _run_matchers("a", [DummyGrammar()])
    assert len(out2) == 1
    out3 = run_matchers("a", [DummyGrammar()])
    assert len(out3) == 1

    # anchor prefilter skip
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

    out_skip = _run_matchers("hello", [SkipGrammar()])
    assert out_skip == []

    # view branching
    @dataclass(frozen=True, slots=True)
    class CaseMatcher:
        anchors: AnchorSet = AnchorSet()
        view: str | None = "casefolded"

        def match(self, view: View) -> list[tuple[int, int]]:
            assert view.subject == view.subject.lower()
            return [(0, 5)]

        def emit(self, span: tuple[int, int], ctx: ScanContext) -> str:
            return "C"

    @dataclass(frozen=True, slots=True)
    class NormMatcher:
        anchors: AnchorSet = AnchorSet()
        view: str | None = "normalized"

        def match(self, view: View) -> list[tuple[int, int]]:
            return [(0, 2)]

        def emit(self, span: tuple[int, int], ctx: ScanContext) -> str:
            return "N"

    @dataclass(frozen=True, slots=True)
    class UnknownViewMatcher:
        anchors: AnchorSet = AnchorSet()
        view: str | None = "custom"

        def match(self, view: View) -> list[tuple[int, int]]:
            return [(0, 1)]

        def emit(self, span: tuple[int, int], ctx: ScanContext) -> str:
            return "U"

    # Wrap each matcher in a grammar container
    @dataclass(frozen=True, slots=True)
    class GCase:
        matchers: tuple[CaseMatcher, ...] = (CaseMatcher(),)

    @dataclass(frozen=True, slots=True)
    class GNorm:
        matchers: tuple[NormMatcher, ...] = (NormMatcher(),)

    @dataclass(frozen=True, slots=True)
    class GUnknown:
        matchers: tuple[UnknownViewMatcher, ...] = (UnknownViewMatcher(),)

    out_views = _run_matchers(
        "Hello",
        [DummyGrammar(), GCase(), GNorm(), GUnknown()],  # type: ignore
    )
    assert len(out_views) >= 4


def test_engine_loop_emit_view_span_fallback() -> None:
    from dataclasses import dataclass

    @dataclass(frozen=True, slots=True)
    class ViewSpanEmitMatcher:
        anchors: AnchorSet = AnchorSet()
        view: str | None = None

        def match(self, view: View) -> list[tuple[int, int]]:
            return [(0, 2)]

        def emit(self, span: tuple[int, int], ctx: ScanContext) -> str:
            # expects view span, not original (fallback path)
            raise TypeError("view span")

    # engine tries (o_s,o_e) then fallback to span on TypeError
    # Test fallback by having emit raise once then succeed
    calls = {"n": 0}

    @dataclass(frozen=True, slots=True)
    class FlakyMatcher:
        anchors: AnchorSet = AnchorSet()
        view: str | None = None

        def match(self, view: View) -> list[tuple[int, int]]:
            return [(0, 2)]

        def emit(self, span: tuple[int, int], ctx: ScanContext) -> str:
            calls["n"] += 1
            if calls["n"] == 1:
                raise TypeError("first fail")
            return "ok"

    # This will trigger fallback per match
    out = _run_matchers("ab", [type("G", (), {"matchers": (FlakyMatcher(),)})()])
    assert out[0].notation == "ok"


def test_anchors_pass_keyset() -> None:
    ctx = ScanContext.of("United States")
    a = AnchorSet(key_sets=(frozenset({"U"}),))
    assert a.passes("United", ctx) is True
    a2 = AnchorSet(key_sets=(frozenset({"Z"}),))
    assert a2.passes("United", ctx) is False


def test_boundary_spec_consuming() -> None:
    assert BoundarySpec.IPV6_TOKEN.is_consuming is True
    assert BoundarySpec.WORD.is_consuming is False
