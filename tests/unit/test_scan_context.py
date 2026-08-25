"""Unit tests for ScanContext substrate (D1–D3)."""

from __future__ import annotations

import pytest

from paxman.core.grammar.scan_context import ScanContext


def test_word_spans_single_pass() -> None:
    ctx = ScanContext.of("hello world 123")
    assert ctx.text == "hello world 123"
    assert ctx.word_spans == ((0, 5), (6, 11), (12, 15))
    assert ctx.word_spans is ctx.word_spans  # memoised identity


def test_empty_text() -> None:
    ctx = ScanContext.of("")
    assert ctx.word_spans == ()
    assert ctx.text == ""


def test_view_identity_no_offsets() -> None:
    ctx = ScanContext.of("Hello World")
    view = ctx.view("casefolded", lambda t: (t.lower(), None))
    assert view.subject == "hello world"
    assert view.offsets is None
    assert view.original_span(0, 5) == (0, 5)
    assert ctx.text[0:5] == "Hello"
    assert view.subject[0:5] == "hello"


def test_view_offset_map_invariant_length_changing() -> None:
    def collapse_double(s: str) -> tuple[str, tuple[int, ...] | None]:
        if "  " not in s:
            return s, None
        return "ab", (0, 3, 4)

    ctx = ScanContext.of("a  b")
    view = ctx.view("compact", collapse_double)
    assert view.subject == "ab"
    assert view.offsets == (0, 3, 4)
    assert len(view.offsets) == len(view.subject) + 1
    assert view.original_span(0, 1) == (0, 3)
    assert view.original_span(1, 2) == (3, 4)
    assert view.original_span(0, 2) == (0, 4)
    assert ctx.text[view.original_span(0, 2)[0] : view.original_span(0, 2)[1]] == "a  b"


def test_raw_text_validation_contract() -> None:
    ctx = ScanContext.of("abc def")
    view = ctx.view("orig", lambda t: (t, None))
    for s, e in [(0, 3), (4, 7)]:
        o_s, o_e = view.original_span(s, e)
        assert ctx.text[o_s:o_e] == view.subject[s:e]


def test_scan_context_is_frozen_slots() -> None:
    ctx = ScanContext.of("x")
    with pytest.raises(AttributeError):
        ctx.text = "y"  # type: ignore[misc]
    assert not hasattr(ctx, "__dict__")
    assert ScanContext.__dataclass_params__.frozen is True


def test_word_spans_shared_across_views() -> None:
    ctx = ScanContext.of("one two three")
    v1 = ctx.view("v1", lambda t: (t.lower(), None))
    v2 = ctx.view("v2", lambda t: (t.upper(), None))
    assert ctx.word_spans == ((0, 3), (4, 7), (8, 13))
    assert v1.subject == "one two three"
    assert v2.subject == "ONE TWO THREE"
