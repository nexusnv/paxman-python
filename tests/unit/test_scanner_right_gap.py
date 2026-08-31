import pytest

from paxman.core.grammar.boundary_spec import BoundarySpec
from paxman.core.grammar.matchers.scanner import ScannerMatcher
from paxman.core.grammar.scan_context import View

pytestmark = pytest.mark.unit


def _gap_view_right(stripped: str | None) -> View:
    """View over original "AB\\tX" → subject "ABX" with gap before X at end.

    Original indices: A[0,1), B[1,2), \\t[2,3) stripped, X[3,4). Subject "ABX" len 3:
    - subject[0]='A' maps to [0,1)
    - subject[1]='B' maps to [1,2)
    - subject[2]='X' maps to [3,4)
    Hit (0,2) "AB" has right neighbor in original '\\t', not 'X', so
    view-level right guard would see 'X' (forbidden) but engine would see '\\t' (pass).
    """
    return View(
        subject="ABX",
        source_starts=(0, 1, 3),
        source_ends=(1, 2, 4),
        _text_len=4,
        stripped_chars=stripped,
    )


def _scan_ab(view: View, pos: int):
    return (2, None) if pos == 0 else None


def test_scanner_defers_right_gap_when_stripped():
    """Right gap + stripped_chars set → view-level right check deferred."""
    m = ScannerMatcher(
        scan=_scan_ab,
        boundary=BoundarySpec(left=None, right=("X",), mode="zero_width"),
        emit=lambda s, c: s,
    )
    assert m.match(_gap_view_right("\t")) == [(0, 2)]


def test_scanner_checks_right_gap_without_stripped():
    """Same gap, no stripped_chars → deferral must NOT apply, right guard fires."""
    m = ScannerMatcher(
        scan=_scan_ab,
        boundary=BoundarySpec(left=None, right=("X",), mode="zero_width"),
        emit=lambda s, c: s,
    )
    assert m.match(_gap_view_right(None)) == []
    assert m.match(_gap_view_right("")) == []
