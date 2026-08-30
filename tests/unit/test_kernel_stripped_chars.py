"""Kernel stripped_chars flag — data-driven view stripping (#87, #88).

Task 1 items are covered here (View/ScanContext carry ``stripped_chars``
as data); later tasks extend this module:

- View/ScanContext carry stripped_chars as data (Task 1) — covered
- engine_loop consumes the flag instead of view_name == "idna" (Task 2)
- boundary re-check ordering before trailing extension (Task 3)
- scanner left-boundary deferral keyed on the flag (Task 4)
- CandidatesMatcher single-pass boundary filter (Task 5)
- acceptance: no `== "idna"` magic-name comparison in paxman/core (Task 6)
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from paxman.core.grammar.boundary_spec import BoundarySpec
from paxman.core.grammar.engine_loop import (
    _VIEW_REGISTRY,
    run_matchers_with_context,
)
from paxman.core.grammar.matchers.scanner import ScannerMatcher
from paxman.core.grammar.normalizers import CaseFold, IDNAFold, StripSeparators
from paxman.core.grammar.scan_context import ScanContext, View

pytestmark = pytest.mark.unit


def test_idnafold_declares_stripped_chars() -> None:
    """IDNAFold strips \\t\\n\\r and must declare it as data."""
    assert IDNAFold().stripped_chars == "\t\n\r"


def test_non_absorbing_normalizers_have_no_stripped_chars() -> None:
    """Normalizers whose stripped chars are never re-absorbed must not set the flag."""
    assert getattr(CaseFold(), "stripped_chars", None) is None
    assert getattr(StripSeparators(), "stripped_chars", None) is None


def test_view_defaults_to_no_stripped_chars() -> None:
    """A View built directly (test-double path) defaults to stripped_chars None."""
    view = View(subject="AB", source_starts=(0, 1), source_ends=(1, 2), _text_len=2)
    assert view.stripped_chars is None


def test_scan_context_view_passes_stripped_chars_through() -> None:
    """ScanContext.view forwards the flag into the cached View."""
    nf = IDNAFold()
    ctx = ScanContext.of("a\tb")
    view = ctx.view(nf.name, nf.normalize, stripped_chars=nf.stripped_chars)
    assert view.stripped_chars == "\t\n\r"
    assert ctx.view(nf.name, nf.normalize, stripped_chars=nf.stripped_chars) is view


def _strip_tabs(
    text: str,
) -> tuple[str, tuple[int, ...] | None, tuple[int, ...] | None]:
    """Shared body for the tab-stripping test doubles."""
    chars: list[str] = []
    starts: list[int] = []
    for i, ch in enumerate(text):
        if ch == "\t":
            continue
        chars.append(ch)
        starts.append(i)
    subject = "".join(chars)
    if len(subject) == len(text):
        return subject, None, None
    return subject, tuple(starts), tuple(s + 1 for s in starts)


class _TabStrip:
    """Test normalizer stripping \\t with offset maps; declares stripped_chars."""

    name = "tstrip"
    provenance = None
    stripped_chars = "\t"

    def normalize(
        self, text: str
    ) -> tuple[str, tuple[int, ...] | None, tuple[int, ...] | None]:
        return _strip_tabs(text)


class _TabStripNoFlag:
    """Same stripping as _TabStrip but WITHOUT the stripped_chars flag."""

    name = "tstrip_noflag"
    provenance = None
    stripped_chars: str | None = None

    def normalize(
        self, text: str
    ) -> tuple[str, tuple[int, ...] | None, tuple[int, ...] | None]:
        return _strip_tabs(text)


def _scan_fixed(view: View, pos: int) -> tuple[int, None] | None:
    """Toy scanner: one full-subject hit at pos 0."""
    return (len(view.subject), None) if pos == 0 else None


def _run_engine(text: str, matcher: object) -> list[object]:
    ctx = ScanContext.of(text)
    grammar = SimpleNamespace(matchers=[matcher], name="toy")
    return list(run_matchers_with_context(ctx, [grammar]))


def test_stripped_view_extends_over_trailing_stripped_chars(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A view with stripped_chars (any name) gets the trailing extension."""
    monkeypatch.setitem(_VIEW_REGISTRY, "tstrip", _TabStrip())
    matcher = ScannerMatcher(
        scan=_scan_fixed,
        view_name="tstrip",
        emit=lambda span, ctx: span,
    )
    out = _run_engine("A:0\t", matcher)
    assert [(m.start, m.end, m.raw_text) for m in out] == [(0, 4, "A:0\t")]


def test_normalizer_without_flag_does_not_extend(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A normalizer with no stripped_chars flag gets no trailing extension.

    The view strips the tab (subject "A:0", len 3) so the span maps to
    (0, 3); without the flag the engine must NOT re-absorb the tab.
    """
    monkeypatch.setitem(_VIEW_REGISTRY, "tstrip_noflag", _TabStripNoFlag())
    matcher = ScannerMatcher(
        scan=_scan_fixed,
        view_name="tstrip_noflag",
        emit=lambda span, ctx: span,
    )
    out = _run_engine("A:0\t", matcher)
    assert [(m.start, m.end, m.raw_text) for m in out] == [(0, 3, "A:0")]


def test_boundary_checked_before_trailing_extension() -> None:
    """(#88) The right guard must see the immediate neighbor (the tab),
    not the char after the stripped run."""
    text = "A:0\tB"
    # idna view: subject "A:0B", the hit (0,3) maps to original (0,3) and
    # the trailing tab is re-absorbable. Right guard forbids the tab, so
    # the pre-extension check must reject the hit.
    matcher = ScannerMatcher(
        scan=lambda view, pos: (3, None) if pos == 0 else None,
        view_name="idna",
        boundary=BoundarySpec(left=None, right=(r"\t",), mode="zero_width"),
        emit=lambda span, ctx: span,
    )
    out = _run_engine(text, matcher)
    assert out == []
