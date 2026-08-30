"""Kernel stripped_chars flag — data-driven view stripping (#87, #88).

Covers:
- View/ScanContext carry stripped_chars as data (Task 1)
- engine_loop consumes the flag instead of view_name == "idna" (Task 2)
- boundary re-check ordering before trailing extension (Task 3)
- scanner left-boundary deferral keyed on the flag (Task 4)
- CandidatesMatcher single-pass boundary filter (Task 5)
- acceptance: no `== "idna"` magic-name comparison in paxman/core (Task 6)
"""

from __future__ import annotations

import pytest

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
    ctx = ScanContext.of("a\tb")
    view = ctx.view("tstrip", IDNAFold().normalize, stripped_chars="\t\n\r")
    assert view.stripped_chars == "\t\n\r"
    assert ctx.view("tstrip", IDNAFold().normalize, stripped_chars="\t\n\r") is view
