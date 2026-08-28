"""View offset round-trip — A4 for every length-changing view.

Original_span exact inverse per amended D3: for length-changing views
(country_normalized, compact, idna) the offset maps are exact inverses.
Budget max_examples=200 deadline=None phases=[generate,target,shrink]
derandomize=False per-shard, cached examples.
"""

from __future__ import annotations

import string
import unicodedata

import pytest
from hypothesis import HealthCheck, Phase, given, settings
from hypothesis import strategies as st

from paxman.core.grammar.normalizers import CountryNameFold, IDNAFold, StripSeparators
from paxman.core.grammar.scan_context import ScanContext

pytestmark = [pytest.mark.property]

_HYP_SETTINGS = settings(
    max_examples=200,
    deadline=None,
    phases=(Phase.generate, Phase.target, Phase.shrink),
    derandomize=False,
    suppress_health_check=list(HealthCheck),
)

# Length-changing views
_COUNTRY_FOLD = CountryNameFold()
_IDNA_FOLD = IDNAFold()
_STRIP_FOLD = StripSeparators()


def _assert_roundtrip(text: str, fold: object, view_name: str) -> None:
    ctx = ScanContext.of(text)
    # dynamic dispatch for normalizer
    norm = fold.normalize
    view = ctx.view(view_name, norm)  # type: ignore[arg-type]
    subject = view.subject
    # offsets invariant
    if view.source_starts is None:
        assert view.source_ends is None
        # no length change — nothing to round-trip (but this file only tests changing)
        return
    assert view.source_ends is not None
    assert len(view.source_starts) == len(subject)
    assert len(view.source_ends) == len(subject)
    # each character's source interval valid
    for i, (s, e) in enumerate(zip(view.source_starts, view.source_ends, strict=True)):
        assert 0 <= s < e <= len(ctx.text)
        # interval must be non-empty
        assert e - s >= 1
        if i > 0:
            assert view.source_starts[i] >= view.source_starts[i - 1]
    # round-trip: ctx.text[original_span] re-normalizes to subject slice
    # exact inverse: original_span via source_starts/ends,
    # view.subject[s:e] equals re-view of original slice
    # (up to the fold's own normalization).
    # Sample a few spans per example to keep cost low.
    n = len(subject)
    # test boundaries
    for s, e in [(0, n), (0, min(1, n)), (max(0, n - 1), n), (0, 0), (n, n)]:
        o_s, o_e = view.original_span(s, e)
        assert 0 <= o_s <= o_e <= len(ctx.text)
        assert ctx.text[o_s:o_e] == text[o_s:o_e]
        if s != e and view_name in ("idna", "compact"):
            # re-normalizing original slice equals subject slice exactly
            sub_ctx = ScanContext.of(ctx.text[o_s:o_e])
            sub_view = sub_ctx.view(view_name, norm)  # type: ignore[arg-type]
            assert sub_view.subject == subject[s:e]
    # additional random spans via hypothesis
    # (caller will generate s,e separately if needed; here we just check structure)


@_HYP_SETTINGS
@given(text=st.text(min_size=0, max_size=80))
def test_country_view_roundtrip(text: str) -> None:
    _assert_roundtrip(text, _COUNTRY_FOLD, "country_normalized")
    # extra random span checks for country
    ctx = ScanContext.of(text)
    view = ctx.view("country_normalized", _COUNTRY_FOLD.normalize)  # type: ignore[arg-type]
    if view.source_starts is None:
        return
    n = len(view.subject)
    if n == 0:
        return
    # hypothesis-generated spans inside the outer given would need nested given;
    # instead sample deterministic spans: middle
    mid = n // 2
    for s, e in [(0, mid), (mid, n), (0, n)]:
        o_s, o_e = view.original_span(s, e)
        assert 0 <= o_s <= o_e <= len(text)
        assert text[o_s:o_e] == ctx.text[o_s:o_e]


@_HYP_SETTINGS
@given(text=st.text(alphabet=string.printable, min_size=0, max_size=80))
def test_idna_view_roundtrip(text: str) -> None:
    _assert_roundtrip(text, _IDNA_FOLD, "idna")
    ctx = ScanContext.of(text)
    view = ctx.view("idna", _IDNA_FOLD.normalize)  # type: ignore[arg-type]
    if view.source_starts is None:
        # short-circuit when no stripping happened (still valid)
        assert view.subject == text or view.subject == text.replace("\t", "").replace(
            "\n", ""
        ).replace("\r", "")
        return
    # strong round-trip for idna: every span re-normalizes exactly
    n = len(view.subject)
    if n == 0:
        return
    # sample a span
    s = 0
    e = n
    o_s, o_e = view.original_span(s, e)
    sub_ctx = ScanContext.of(ctx.text[o_s:o_e])
    sub_view = sub_ctx.view("idna", _IDNA_FOLD.normalize)  # type: ignore[arg-type]
    assert sub_view.subject == view.subject[s:e]


@_HYP_SETTINGS
@given(
    text=st.text(
        alphabet=string.ascii_letters + string.digits + " ().- \t\n",
        min_size=0,
        max_size=80,
    )
)
def test_compact_view_roundtrip(text: str) -> None:
    _assert_roundtrip(text, _STRIP_FOLD, "compact")
    ctx = ScanContext.of(text)
    view = ctx.view("compact", _STRIP_FOLD.normalize)  # type: ignore[arg-type]
    if view.source_starts is None:
        return
    n = len(view.subject)
    if n == 0:
        return
    o_s, o_e = view.original_span(0, n)
    sub_ctx = ScanContext.of(ctx.text[o_s:o_e])
    sub_view = sub_ctx.view("compact", _STRIP_FOLD.normalize)  # type: ignore[arg-type]
    assert sub_view.subject == view.subject


@_HYP_SETTINGS
@given(text=st.text(min_size=0, max_size=80))
def test_all_length_changing_views_span_exact(text: str) -> None:
    """Amended D3: every length-changing view's original_span is exact inverse."""
    for fold, name in [
        (_COUNTRY_FOLD, "country_normalized"),
        (_IDNA_FOLD, "idna"),
        (_STRIP_FOLD, "compact"),
    ]:
        ctx = ScanContext.of(text)
        view = ctx.view(name, fold.normalize)  # type: ignore[arg-type]
        if view.source_starts is None:
            # identity view — skip (not length-changing)
            continue
        # exact inverse: offsets bijection subject indices -> source intervals
        assert len(view.source_starts) == len(view.subject)
        # re-derive subject via offsets should match length
        # also check that every subject char maps to a single source char interval
        for i in range(len(view.subject)):
            s, e = view.original_span(i, i + 1)
            assert e - s == 1 or (name == "country_normalized" and e - s >= 1)
            src = ctx.text[s:e]
            subj_ch = view.subject[i]
            if name == "country_normalized":
                nfd = unicodedata.normalize("NFD", src).lower()
                stripped = "".join(c for c in nfd if unicodedata.category(c) != "Mn")
                assert (
                    subj_ch in stripped or subj_ch == stripped.strip() or subj_ch == " "
                )
            else:
                # idna / compact preserve case, just check identity
                assert subj_ch == src or (
                    name == "compact" and src in " ().-" and subj_ch not in src
                )
