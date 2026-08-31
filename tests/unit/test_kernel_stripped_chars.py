"""Kernel stripped_chars flag — data-driven view stripping (#87, #88).

Coverage:

- View/ScanContext carry ``stripped_chars`` as data
- engine_loop consumes the flag (no ``view_name == "idna"`` comparisons)
- boundary re-check ordering before trailing stripped-char extension (#88)
- scanner left-boundary deferral keyed on the flag
- CandidatesMatcher single-pass boundary filter (#68)
- acceptance: no ``== "idna"`` magic-name comparison in paxman/core
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from paxman.core.grammar.boundary_spec import BoundarySpec
from paxman.core.grammar.engine_loop import (
    _VIEW_REGISTRY,
    run_matchers_with_context,
)
from paxman.core.grammar.matchers.candidates import (
    CandidatesMatcher,
    get_flat_for_matcher,
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


def test_boundary_checked_before_trailing_extension(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """(#88) The right guard must see the immediate neighbor (the tab),
    not the char after the stripped run."""
    monkeypatch.setitem(_VIEW_REGISTRY, "tstrip", _TabStrip())
    matcher = ScannerMatcher(
        scan=lambda view, pos: (3, None) if pos == 0 else None,
        view_name="tstrip",
        boundary=BoundarySpec(left=None, right=(r"\t",), mode="zero_width"),
        emit=lambda span, ctx: span,
    )
    out = _run_engine("A:0\tB", matcher)
    assert out == []


def test_boundary_pass_still_extends_and_emits(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """(#88) A right guard that passes pre-extension must not block the
    trailing extension — the re-check is a gate, not a span change."""
    monkeypatch.setitem(_VIEW_REGISTRY, "tstrip", _TabStrip())
    matcher = ScannerMatcher(
        scan=lambda view, pos: (3, None) if pos == 0 else None,
        view_name="tstrip",
        boundary=BoundarySpec(left=None, right=("X",), mode="zero_width"),
        emit=lambda span, ctx: span,
    )
    out = _run_engine("A:0\tB", matcher)
    # Span (0, 4) covers "A:0\t" (4 chars) — RecognitionMatch enforces
    # len(raw_text) == end - start.
    assert [(m.start, m.end, m.raw_text) for m in out] == [(0, 4, "A:0\t")]


def _gap_view(stripped: str | None) -> View:
    """View over a 5-char original whose subject 'AB' has a gap before 'B'.

    source maps: 'A' -> [0,1), 'B' -> [3,4); original index 1..2 hold the
    stripped char(s). pos=1 (the 'B' hit) therefore has a stripped gap to
    its left: source_starts[1]=3 != source_ends[0]=1.
    """
    return View(
        subject="AB",
        source_starts=(0, 3),
        source_ends=(1, 4),
        _text_len=4,
        stripped_chars=stripped,
    )


def _scan_at_one(view: View, pos: int) -> tuple[int, None] | None:
    return (2, None) if pos == 1 else None


def test_scanner_defers_left_guard_when_stripped_chars_set() -> None:
    """Gap to the left + stripped_chars set → view-level left check deferred."""
    matcher = ScannerMatcher(
        scan=_scan_at_one,
        boundary=BoundarySpec(left=("A",), right=None, mode="zero_width"),
        emit=lambda span, ctx: span,
    )
    # View-level check would see subject[0] == 'A' (forbidden) and reject;
    # the deferral keys on view.stripped_chars, not the view name.
    assert matcher.match(_gap_view("\t")) == [(1, 2)]


@pytest.mark.parametrize("stripped", [None, ""])
def test_scanner_checks_left_guard_without_stripped_chars(
    stripped: str | None,
) -> None:
    """Same gap, falsy stripped_chars (None or "") → deferral must NOT apply."""
    matcher = ScannerMatcher(
        scan=_scan_at_one,
        boundary=BoundarySpec(left=("A",), right=None, mode="zero_width"),
        emit=lambda span, ctx: span,
    )
    assert matcher.match(_gap_view(stripped)) == []


def test_engine_boundary_recheck_is_data_driven(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Engine re-checks the original text for ANY stripped view (not just idna)."""
    monkeypatch.setitem(_VIEW_REGISTRY, "tstrip", _TabStrip())
    # text "a\tb:0": view strips the tab → subject "ab:0"; hit (1,4) maps to
    # original (2,5) whose LEFT neighbor text[1] is the stripped tab. The
    # left guard forbids the tab, so the engine-level re-check must reject.
    matcher = ScannerMatcher(
        scan=lambda view, pos: (4, None) if pos == 1 else None,
        view_name="tstrip",
        boundary=BoundarySpec(left=(r"\t",), right=None, mode="zero_width"),
        emit=lambda span, ctx: span,
    )
    assert _run_engine("a\tb:0", matcher) == []


class _FakeCandidate:
    """Minimal candidate double: frozen spans, pass-through emit."""

    digest = "fake-candidate"

    def __init__(self, spans: tuple[tuple[int, int], ...]) -> None:
        self._spans = spans

    def match(self, view: View) -> list[tuple[int, int]]:
        return list(self._spans)

    def emit(self, span: tuple[int, int], ctx: object) -> tuple[int, int]:
        return span


def _result_flat_pair(
    m: CandidatesMatcher,
) -> tuple[list[tuple[int, int]], list[tuple[int, int, int]]]:
    spans = m.match(ScanContext.of("a1b").view("orig", lambda t: (t, None, None)))
    return spans, get_flat_for_matcher(m)


def test_candidates_boundary_filter_all_strategy() -> None:
    """strategy=all: boundary-filtered spans, flat mirrors result exactly."""
    m = CandidatesMatcher(
        candidates=(_FakeCandidate(((2, 3),)), _FakeCandidate(((0, 1),))),
        strategy="all",
        boundary=BoundarySpec(left=(r"\d",), right=None, mode="zero_width"),
    )
    spans, flat = _result_flat_pair(m)
    # span (2,3) 'b' has left neighbor '1' (digit) → filtered out.
    assert spans == [(0, 1)]
    assert [(s, e) for s, e, _ in flat] == spans


def test_candidates_boundary_filter_first_strategy() -> None:
    """strategy=first: dedup + boundary filter compose; flat mirrors result."""
    m = CandidatesMatcher(
        candidates=(_FakeCandidate(((2, 3), (0, 1), (0, 1))),),
        strategy="first",
        boundary=BoundarySpec(left=(r"\d",), right=None, mode="zero_width"),
    )
    spans, flat = _result_flat_pair(m)
    assert spans == [(0, 1)]
    assert [(s, e) for s, e, _ in flat] == spans


def test_no_magic_idna_view_name_comparison_in_core() -> None:
    """(#87 acceptance) No `== "idna"` comparison remains in paxman/core."""
    import re
    from pathlib import Path

    core = Path(__file__).resolve().parents[2] / "paxman" / "core"
    offenders: list[str] = []
    for path in sorted(core.rglob("*.py")):
        for lineno, line in enumerate(
            path.read_text(encoding="utf-8").splitlines(), start=1
        ):
            if re.search(r'==\s*"idna"', line):
                offenders.append(f"{path.relative_to(core)}:{lineno}: {line.strip()}")
    assert offenders == [], "magic view-name comparison(s) found:\n" + "\n".join(
        offenders
    )
