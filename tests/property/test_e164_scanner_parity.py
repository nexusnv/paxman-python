"""Parity shard — scanner Phone E.164 15-digit bounded window (ADR §9.3)."""

from __future__ import annotations

import pathlib

import pytest

from paxman.capabilities.Phone.grammar.e164_recognition import E164Grammar
from paxman.core.grammar import BoundarySpec, ScannerMatcher
from tests.property._legacy_phone_url_grammars import LegacyE164Grammar
from tests.property.grammar_kernel_parity import assert_kernel_parity

pytestmark = [pytest.mark.property]


def test_e164_uses_scanner_matcher() -> None:
    g = E164Grammar()
    assert hasattr(g, "matchers"), "E164Grammar must expose matchers"
    matchers = g.matchers
    assert matchers is not None
    assert len(matchers) == 1
    m = matchers[0]
    assert isinstance(m, ScannerMatcher)
    assert m.boundary == BoundarySpec.E164_LEFT
    # 15-digit bound as data; char window larger for separators
    assert m.max_window >= 15
    src = pathlib.Path(
        "paxman/capabilities/Phone/grammar/e164_recognition.py"
    ).read_text()
    assert "PostStage" not in src
    assert "RegexStage" not in src
    assert "_E164_PATTERN" not in src
    assert "_e164_trim" not in src
    assert "ScannerMatcher" in src
    assert "max_window" in src
    assert "_MAX_E164_DIGITS" in src


# Golden corpus from pre-migration grammar — valid, separators, runaway trim,
# oversized, rejections, in-text, trailing period.
_CORPUS: tuple[str, ...] = (
    "+15551234567",
    "+1 555 123 4567",
    "+44-20-7946-0958",
    "+1.555.123.4567",
    "+1 (555) 123-4567",
    "+15551234567 5551234567",
    "+12345678901234567890",
    "15551234567",
    "(555) 123-4567",
    "user+123@example.com",
    "a+123",
    "x+11=y",
    "1+11=12",
    "Call +1 555 123 4567 now",
    "+15551234567 or +442079460958",
    "End of +15551234567.",
    "Call me at +15551234567 today",
    "+44 20 7946 0958.",
    "tel:+15551234567",
    "",
    "   ",
    "+1",
    "++15551234567",
)


@pytest.mark.parametrize("text", _CORPUS)
def test_e164_scanner_parity_byte_identical(text: str) -> None:
    assert_kernel_parity(LegacyE164Grammar(), E164Grammar(), text)


def test_e164_scanner_parity_corpus_len() -> None:
    assert len(_CORPUS) >= 20
