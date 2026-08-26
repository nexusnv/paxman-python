"""Boost coverage for kernel additions."""

from __future__ import annotations

import pytest

from paxman.core.grammar.anchors import AnchorSet
from paxman.core.grammar.boundary_spec import BoundarySpec, check_boundary
from paxman.core.grammar.engine_loop import (
    _run_matchers,
    _run_matchers_with_context,
    run_matchers,
)
from paxman.core.grammar.matchers.candidates import CandidatesMatcher
from paxman.core.grammar.matchers.combinator import CombinatorMatcher
from paxman.core.grammar.matchers.label import LabelMatcher
from paxman.core.grammar.matchers.lexicon import LexiconMatcher
from paxman.core.grammar.matchers.property import PropertyMatcher
from paxman.core.grammar.matchers.regex import RegexMatcher
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
    assert (
        m.match(View(subject="A", source_starts=None, source_ends=None, _text_len=1))
        == []
    )


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

    # bad offsets length — starts len != subject len
    def bad_len(s: str) -> tuple[str, tuple[int, ...] | None, tuple[int, ...] | None]:
        return "hi", (0,), (1,)

    with pytest.raises(AssertionError):
        ctx.view("bad", bad_len)

    # empty interval — 0 < ends fails
    def bad_interval(
        s: str,
    ) -> tuple[str, tuple[int, ...] | None, tuple[int, ...] | None]:
        return "ab", (0, 0), (0, 5)

    ctx2 = ScanContext.of("hello")
    with pytest.raises(AssertionError):
        ctx2.view("bad2", bad_interval)


def test_scan_context_view_caching() -> None:
    ctx = ScanContext.of("hello world")
    v1 = ctx.view("case", lambda t: (t.lower(), None, None))
    v2 = ctx.view("case", lambda t: (t.upper(), None, None))
    assert v1 is v2
    assert v1.subject == "hello world"


def test_view_original_span_with_offsets() -> None:
    ctx = ScanContext.of("a  b")
    view = ctx.view("c", lambda t: ("ab", (0, 3), (1, 4)))
    assert view.original_span(0, 2) == (0, 4)
    assert view.original_span(1, 2) == (3, 4)


def test_check_boundary_left_right() -> None:
    assert check_boundary("x y", 2, 3, BoundarySpec.WORD) is True
    # left char is 'x' which is \w, should block WORD
    assert check_boundary("x y", 1, 2, BoundarySpec.WORD) is False
    # right check: "a b" span "a" at 0,1 -> suffix " b" starts with " " not \w so passes
    assert check_boundary("a b", 0, 1, BoundarySpec.WORD) is True
    # blocked right: "ab" span "a" -> next char "b" is \w -> block
    assert check_boundary("ab", 0, 1, BoundarySpec.WORD) is False
    # degree sign
    assert BoundarySpec.DEGREE_WORD_SIGN.left is not None


def test_normalizer_sequence_offsets() -> None:
    seq = NormalizerSequence(steps=(StripSeparators(), CaseFold()))
    subj, starts, ends = seq.normalize("+1 (555) 123-4567")
    assert subj == "+15551234567"
    assert starts is not None and ends is not None
    seq2 = NormalizerSequence(steps=(CaseFold(), SeparatorFold()))
    subj2, starts2, ends2 = seq2.normalize("Hello_World")
    assert subj2 == "hello-world"
    assert starts2 is None and ends2 is None
    assert seq2.name == "casefolded+normalized"
    assert seq2.provenance is not None


def test_country_name_fold_empty_and_identity() -> None:
    nf = CountryNameFold()
    subj, starts, ends = nf.normalize("")
    assert subj == ""
    assert starts == () and ends == ()
    subj2, starts2, ends2 = nf.normalize("hello")
    assert subj2 == "hello"
    assert starts2 is None and ends2 is None
    subj3, starts3, ends3 = nf.normalize("Côte d'Ivoire")
    assert "cote" in subj3
    _ = starts3
    _ = ends3
    subj4, _, _ = nf.normalize("United\u2013States")
    assert "united states" in subj4


def test_accent_strip_and_symbol_fold() -> None:
    assert AccentStrip().normalize("Côte")[0] == "cote"
    assert SymbolFold().normalize("a²")[0] == "a2"
    assert SeparatorFold().normalize("a_b")[0] == "a-b"
    assert CaseFold().normalize("ABC")[0] == "abc"


def test_idna_fold_tab() -> None:
    nf = IDNAFold()
    subj, starts, ends = nf.normalize("a\tb\nc")
    assert subj == "abc"
    assert starts is not None and ends is not None
    subj2, starts2, ends2 = nf.normalize("abc")
    assert starts2 is None and ends2 is None
    _ = subj2


def test_strip_separators_no_change() -> None:
    nf = StripSeparators()
    subj, starts, ends = nf.normalize("15551234567")
    assert starts is None and ends is None
    _ = subj
    subj2, starts2, ends2 = nf.normalize("+1-555")
    assert starts2 is not None and ends2 is not None
    _ = subj2
    _ = ends2


def test_lexicon_matcher_alternation_with_boundary() -> None:
    matcher = LexiconMatcher(
        tokens=frozenset({"hello", "world"}),
        boundary=BoundarySpec.WORD,
        representation="alternation",
    )
    ctx = ScanContext.of("hello world")
    view = ctx.view("orig", lambda t: (t, None, None))
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
    view2 = ctx2.view("orig", lambda t: (t, None, None))
    assert matcher2.match(view2) == []


def test_lexicon_matcher_trie_longest() -> None:
    tokens = frozenset({"a", "ab", "abc", "hello world"})
    # force trie by passing representation trie or >500
    m = LexiconMatcher(tokens=tokens, boundary=None, representation="trie")
    ctx = ScanContext.of("abc hello world")
    view = ctx.view("orig", lambda t: (t, None, None))
    spans = m.match(view)
    assert (0, 3) in spans  # longest abc
    # hello world spans 4..15?
    assert any(s == 4 and e - s == 11 for s, e in spans)
    # word anchored: inside word not matched
    m2 = LexiconMatcher(tokens=frozenset({"ell"}), representation="trie")
    ctx2 = ScanContext.of("hello")
    view2 = ctx2.view("orig", lambda t: (t, None, None))
    assert m2.match(view2) == []


def test_lexicon_matcher_trie_boundary() -> None:
    m = LexiconMatcher(
        tokens=frozenset({"hello"}), boundary=BoundarySpec.WORD, representation="trie"
    )
    ctx = ScanContext.of("xhelloy")  # no space -> word anchored no match
    view = ctx.view("orig", lambda t: (t, None, None))
    assert m.match(view) == []
    # but with spaces it matches
    ctx2 = ScanContext.of(" hello ")
    view2 = ctx2.view("orig", lambda t: (t, None, None))
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
    with pytest.raises(
        NotImplementedError, match="CandidatesMatcher not yet implemented"
    ):
        cm.match(View(subject="x", source_starts=None, source_ends=None, _text_len=1))

    cb = CombinatorMatcher(
        expr=("alt", [RegexMatcher(pattern="a", boundary=None, view=None, anchors=AnchorSet())])
    )
    view_cb = View(subject="ab", source_starts=None, source_ends=None, _text_len=2)
    assert cb.match(view_cb) == [(0, 1)]


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
        view: str | None = "country_normalized"

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

    grammars: list[object] = [DummyGrammar(), GCase(), GNorm(), GUnknown()]
    out_views = _run_matchers("Hello", grammars)
    assert len(out_views) >= 4


def test_engine_loop_emit_strict_signature() -> None:
    from dataclasses import dataclass

    # Strict emit: (span, context) -> NotationT where span is original [o_s,o_e).
    # A TypeError inside emit must not be conflated with a signature mismatch;
    # signature is validated via inspect before calling.
    @dataclass(frozen=True, slots=True)
    class DomainErrorMatcher:
        anchors: AnchorSet = AnchorSet()
        view: str | None = None

        def match(self, view: View) -> list[tuple[int, int]]:
            return [(0, 2)]

        def emit(self, span: tuple[int, int], ctx: ScanContext) -> str:
            raise TypeError("domain error inside emit")

    # Domain TypeError propagates as-is (not wrapped as signature mismatch)
    with pytest.raises(TypeError, match="domain error inside emit"):
        _run_matchers("ab", [type("G", (), {"matchers": (DomainErrorMatcher(),)})()])

    # Wrong arity now validated at matcher construction for shipped matchers
    # (see test_emit_arity_validated_at_construction). Dummy matcher without
    # construction validation falls through to Python call-time TypeError.
    @dataclass(frozen=True, slots=True)
    class WrongArityMatcher:
        anchors: AnchorSet = AnchorSet()
        view: str | None = None

        def match(self, view: View) -> list[tuple[int, int]]:
            return [(0, 2)]

        def emit(self, span: tuple[int, int]) -> str:  # type: ignore[no-untyped-def]
            return "bad"

    with pytest.raises(TypeError):
        _run_matchers("ab", [type("G", (), {"matchers": (WrongArityMatcher(),)})()])

    # Happy path: correct arity succeeds
    @dataclass(frozen=True, slots=True)
    class OkMatcher:
        anchors: AnchorSet = AnchorSet()
        view: str | None = None

        def match(self, view: View) -> list[tuple[int, int]]:
            return [(0, 2)]

        def emit(self, span: tuple[int, int], ctx: ScanContext) -> str:
            return "ok"

    out = _run_matchers("ab", [type("G", (), {"matchers": (OkMatcher(),)})()])
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


def test_scan_api_type_errors() -> None:
    from paxman.api.scan import scan
    from paxman.capabilities.Country.capability import CountryCapability
    from paxman.core.discovery import register_capability, reset_registry
    from paxman.core.domain import Mention, ScanResult

    with pytest.raises(TypeError):
        scan(123, [])  # type: ignore[arg-type]
    with pytest.raises(TypeError):
        scan("hello", 123)  # type: ignore[arg-type]
    # valid scan path
    reset_registry()
    register_capability(CountryCapability())
    result = scan("hello United States", [CountryCapability.create_contract()])
    assert isinstance(result, ScanResult)
    assert isinstance(result.mentions, dict)
    m = Mention(span=(0, 1), grammar="g", notation="n", candidates=None)
    assert m.span == (0, 1)
    reset_registry()


def test_emit_arity_validated_at_construction() -> None:
    # ADR §13 R3: emit signature validated once at matcher construction,
    # not per-call via inspect.signature in engine_loop.
    def bad_emit_1(span: tuple[int, int]) -> str:  # type: ignore[no-untyped-def]
        return "bad"

    def bad_emit_3(  # type: ignore[no-untyped-def]
        span: tuple[int, int], ctx: object, extra: object
    ) -> str:
        return "bad"

    def ok_emit(span: tuple[int, int], ctx: object) -> str:  # type: ignore[no-untyped-def]
        return "ok"

    # 1-param emit must fail at construction
    with pytest.raises(TypeError, match="must have 2 params"):
        LexiconMatcher(tokens=frozenset({"hello"}), emit=bad_emit_1)  # type: ignore[arg-type]

    # 3-param emit must fail at construction
    with pytest.raises(TypeError, match="must have 2 params"):
        LexiconMatcher(tokens=frozenset({"hello"}), emit=bad_emit_3)  # type: ignore[arg-type]

    # 2-param emit must succeed
    m = LexiconMatcher(tokens=frozenset({"hello"}), emit=ok_emit)  # type: ignore[arg-type]
    assert m.emit is ok_emit

    # RegexMatcher with bad arity also fails at construction
    with pytest.raises(TypeError, match="must have 2 params"):
        from paxman.core.grammar.matchers.regex import RegexMatcher

        RegexMatcher(pattern="hello", emit=bad_emit_1)  # type: ignore[arg-type]

    # PropertyMatcher with bad arity also fails at construction
    with pytest.raises(TypeError, match="must have 2 params"):
        PropertyMatcher(ranges=((48, 57),), emit=bad_emit_1)  # type: ignore[arg-type]

    # ScannerMatcher with bad arity also fails at construction
    from paxman.core.grammar.matchers.scanner import ScannerMatcher

    def dummy_scan(view: object, pos: int) -> tuple[int, object] | None:  # type: ignore[no-untyped-def]
        return None

    with pytest.raises(TypeError, match="must have 2 params"):
        ScannerMatcher(scan=dummy_scan, emit=bad_emit_1)  # type: ignore[arg-type]

    # CombinatorMatcher with bad arity also fails at construction
    with pytest.raises(TypeError, match="must have 2 params"):
        CombinatorMatcher(expr=("alt", ["a"]), emit=bad_emit_1)  # type: ignore[arg-type]

    # Happy path: good emit for each kind
    from paxman.core.grammar.matchers.regex import RegexMatcher as RegexMatcher2

    rm = RegexMatcher2(pattern="hello", emit=ok_emit)  # type: ignore[arg-type]
    assert rm.emit is ok_emit
    pm = PropertyMatcher(ranges=((48, 57),), emit=ok_emit)  # type: ignore[arg-type]
    assert pm.emit is ok_emit
    sm = ScannerMatcher(scan=dummy_scan, emit=ok_emit)  # type: ignore[arg-type]
    assert sm.emit is ok_emit
    cm = CombinatorMatcher(expr=("alt", ["a"]), emit=ok_emit)  # type: ignore[arg-type]
    assert cm.emit is ok_emit  # type: ignore[attr-defined]
