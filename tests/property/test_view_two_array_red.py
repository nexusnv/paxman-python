"""RED: two-array offset maps — Option 1 exact span-end translation."""

from __future__ import annotations

import pytest

from paxman.core.grammar.normalizers import CountryNameFold, IDNAFold, StripSeparators
from paxman.core.grammar.scan_context import ScanContext

pytestmark = [pytest.mark.property]


def test_country_name_fold_united_states_period_exact_end() -> None:
    """United States. must map to (0,13) not (0,14); raw_text trimmed."""
    text = "United States."
    nf = CountryNameFold()
    subject, starts, ends = nf.normalize(text)  # type: ignore[misc]
    # New triple protocol
    assert subject == "united states"
    assert starts is not None and ends is not None
    assert len(starts) == len(subject)
    assert len(ends) == len(subject)
    # invariant 0<=starts[i]<ends[i]<=len(text)
    for i in range(len(subject)):
        assert 0 <= starts[i] < ends[i] <= len(text)
    ctx = ScanContext.of(text)
    view = ctx.view("country_normalized", nf.normalize)  # type: ignore[arg-type]
    assert view.subject == "united states"
    o_s, o_e = view.original_span(0, len(view.subject))
    assert (o_s, o_e) == (0, 13), (
        f"got {(o_s, o_e)} expected (0,13) — single-array over-extends"
    )
    assert ctx.text[o_s:o_e] == "United States"
    assert view.subject == ctx.text[o_s:o_e].lower()  # without trailing period


def test_trailing_comma_regression() -> None:
    text = "United States of America,"
    nf = CountryNameFold()
    subject, starts, ends = nf.normalize(text)  # type: ignore[misc]
    assert subject == "united states of america"
    ctx = ScanContext.of(text)
    view = ctx.view("country_normalized", nf.normalize)  # type: ignore[arg-type]
    o_s, o_e = view.original_span(0, len(view.subject))
    assert ctx.text[o_s:o_e] == "United States of America"
    assert (o_s, o_e) == (0, 24)


def test_raw_text_invariant_net() -> None:
    text = "Hello United States. world"
    nf = CountryNameFold()
    ctx = ScanContext.of(text)
    view = ctx.view("country_normalized", nf.normalize)  # type: ignore[arg-type]
    # simulate lexicon match for "united states" at view positions
    # find subject index
    idx = view.subject.find("united states")
    assert idx != -1
    o_s, o_e = view.original_span(idx, idx + len("united states"))
    assert ctx.text[o_s:o_e] == "United States"
    assert view.subject[idx : idx + len("united states")] == "united states"


def test_strip_separators_two_array() -> None:
    text = "+1 (555) 123-4567"
    nf = StripSeparators()
    subject, starts, ends = nf.normalize(text)  # type: ignore[misc]
    assert subject == "+15551234567"
    assert starts is not None and ends is not None
    assert len(starts) == len(subject)
    assert len(ends) == len(subject)
    ctx = ScanContext.of(text)
    view = ctx.view("compact", nf.normalize)  # type: ignore[arg-type]
    o_s, o_e = view.original_span(0, len(view.subject))
    # compact removes separators, but end should be len(text) only if last char kept
    # Last char '7' at idx 16 -> ends last =17 len(text)=17
    assert o_e == len(text)
    # Every interval exact
    for i in range(len(subject)):
        assert ctx.text[view.source_starts[i] : view.source_ends[i]] == subject[i]  # type: ignore[attr-defined]


def test_idna_fold_two_array() -> None:
    text = "a\tb\nc"
    nf = IDNAFold()
    subject, starts, ends = nf.normalize(text)  # type: ignore[misc]
    assert subject == "abc"
    assert len(starts) == 3  # type: ignore[arg-type]
    ctx = ScanContext.of(text)
    view = ctx.view("idna", nf.normalize)  # type: ignore[arg-type]
    o_s, o_e = view.original_span(0, 3)
    assert (o_s, o_e) == (0, 5)
    assert ctx.text[o_s:o_e] == "a\tb\nc"
    assert view.source_starts == (0, 2, 4)
    assert view.source_ends == (1, 3, 5)


def test_length_preserving_returns_none_none() -> None:
    from paxman.core.grammar.normalizers import CaseFold

    nf = CaseFold()
    subject, starts, ends = nf.normalize("Hello")  # type: ignore[misc]
    assert subject == "hello"
    assert starts is None and ends is None
    ctx = ScanContext.of("Hello")
    view = ctx.view("casefolded", nf.normalize)  # type: ignore[arg-type]
    assert view.source_starts is None  # type: ignore[attr-defined]
    assert view.source_ends is None  # type: ignore[attr-defined]
    assert view.original_span(0, 3) == (0, 3)


def test_empty_subject_sentinel() -> None:
    nf = CountryNameFold()
    subject, starts, ends = nf.normalize("...")  # type: ignore[misc]
    assert subject == ""
    # empty subject should give empty arrays, view span (0,0)
    ctx = ScanContext.of("...")
    view = ctx.view("country_normalized", nf.normalize)  # type: ignore[arg-type]
    assert view.subject == ""
    assert view.original_span(0, 0) == (0, 0)
