"""Parity shard — view offset round-trip (two-array exact-end)."""

import pytest

from paxman.core.grammar.normalizers import CountryNameFold
from paxman.core.grammar.scan_context import ScanContext
from tests.property.grammar_kernel_parity import assert_kernel_parity

pytestmark = [pytest.mark.property]

assert assert_kernel_parity is not None


def test_view_exact_end_united_states_period() -> None:
    text = "United States."
    nf = CountryNameFold()
    ctx = ScanContext.of(text)
    view = ctx.view("country_normalized", nf.normalize)  # type: ignore[arg-type]
    o_s, o_e = view.original_span(0, len(view.subject))
    assert (o_s, o_e) == (0, 13)
    assert ctx.text[o_s:o_e] == "United States"
    assert view.subject == ctx.text[o_s:o_e].lower()


def test_view_raw_text_invariant() -> None:
    text = "Hello United States. world"
    nf = CountryNameFold()
    ctx = ScanContext.of(text)
    view = ctx.view("country_normalized", nf.normalize)  # type: ignore[arg-type]
    idx = view.subject.find("united states")
    assert idx != -1
    o_s, o_e = view.original_span(idx, idx + len("united states"))
    assert ctx.text[o_s:o_e] == "United States"
    assert view.subject[idx : idx + len("united states")] == "united states"
    assert ctx.text[o_s:o_e] == text[o_s:o_e]
