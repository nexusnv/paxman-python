"""Pin #107 docstring closeout — every CodeRabbit-flagged callable has prose.

Regression guard: the exact public functions flagged in #107 must carry a
non-empty ``__doc__``. Prose-only pin — no behavior assertions.
"""

from __future__ import annotations

import pytest

import tools.regenerate_unicode_property_data as regen
from paxman.core.grammar.matchers.scanner import ScannerMatcher
from paxman.core.grammar.stages import UnicodePropertyStage

pytestmark = pytest.mark.unit

_TARGETS: list[tuple[object, str]] = [
    (UnicodePropertyStage.__post_init__, "UnicodePropertyStage.__post_init__"),
    (UnicodePropertyStage.run, "UnicodePropertyStage.run"),
    (ScannerMatcher.match, "ScannerMatcher.match"),
    (regen._load_snapshot, "_load_snapshot"),
    (regen._parse_ranges, "_parse_ranges"),
    (regen._format_ranges, "_format_ranges"),
    (regen._render, "_render"),
    (regen.main, "main"),
]


@pytest.mark.parametrize(
    ("target", "qualname"), [pytest.param(t, q, id=q) for t, q in _TARGETS]
)
def test_flagged_callable_has_docstring(target: object, qualname: str) -> None:
    """Every #107-flagged callable must carry a non-empty docstring."""
    doc = getattr(target, "__doc__", None)
    assert isinstance(doc, str) and doc.strip(), f"{qualname} is missing a docstring"
