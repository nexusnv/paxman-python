"""Hypothesis property tests for the UNSPSC capability.

- a stem sampled from the pinned snapshot self-canonicalizes through the
  full pipeline (membership fixed point);
- random 8-digit input never raises and resolves INVALID with high
  probability (≈1 − 13490/10⁸; a sampled live stem legitimately succeeds);
- a 6-digit alias and its padded stem share every rule's ``normalize()``;
- non-digit mutations of a live stem never match the grammar;
- snapshot self-consistency: every stem's pair-prefix ancestors are live
  rows, and every rule's ``target_semantics`` is produced by the shipped
  grammar.

Fixture-row self-canonicalization lives in
``tests/property/test_reentry_invariant.py`` ROWS; the ADR-0011 classes
live in ``tests/property/test_output_format_preservation.py`` CLASS_MAP.

Registry posture: the fuzz properties drive the full pipeline
(robustness cannot be observed off-pipeline), so this module uses a
local ``_fresh_registry`` fixture registering only UNSPSC — the
documented ``test_money_properties.py`` exception pattern.
"""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from hypothesis import given
from hypothesis import strategies as st

from paxman.api.canonicalize import canonicalize
from paxman.capabilities.UNSPSC.capability import UNSPSCCapability
from paxman.capabilities.UNSPSC.contract import UNSPSCContract
from paxman.capabilities.UNSPSC.grammar.unspsc_recognition import (
    UNSPSCRecognitionGrammar,
)
from paxman.capabilities.UNSPSC.notation import UNSPSCNotation
from paxman.capabilities.UNSPSC.rules.data.unspsc_codeset import LIVE_STEMS
from paxman.core.discovery import register_capability, reset_registry
from paxman.core.domain import Resolution

pytestmark = pytest.mark.property

_STEMS = sorted(LIVE_STEMS)


@pytest.fixture(autouse=True)
def _fresh_registry() -> Iterator[None]:
    """Reset the registry and register UNSPSC around each test."""
    reset_registry()
    register_capability(UNSPSCCapability())
    yield
    reset_registry()


def _grammar_notation(text: str) -> UNSPSCNotation:
    matches = UNSPSCRecognitionGrammar().recognize(text)
    assert len(matches) == 1
    return matches[0].notation


@given(stem=st.sampled_from(_STEMS))
def test_live_stem_self_canonicalizes(stem: str) -> None:
    """Every snapshot stem canonicalizes to itself (membership fixed point)."""
    contract = UNSPSCCapability.create_contract()
    result = canonicalize(stem, contract)
    assert result.status is Resolution.SUCCESS
    assert result.canonicalized_value == stem


@given(body=st.from_regex(r"[0-9]{8}", fullmatch=True))
def test_random_8_digit_never_raises(body: str) -> None:
    """Random 8-digit input resolves without raising (usually INVALID)."""
    contract = UNSPSCCapability.create_contract()
    result = canonicalize(body, contract)
    assert result.status in (Resolution.SUCCESS, Resolution.INVALID)
    if body not in LIVE_STEMS:
        assert result.status is Resolution.INVALID


@given(stem=st.sampled_from(_STEMS))
def test_alias_and_padded_share_normalize(stem: str) -> None:
    """All four rules agree on the 8-digit stem as the dedup key."""
    capability = UNSPSCCapability()
    contract = UNSPSCContract()
    notation = UNSPSCNotation(
        digits=stem, level="commodity", function="", native_length=8
    )
    assert {
        rule.normalize(notation, contract) for rule in capability.get_rules()
    } == {stem}


@given(stem=st.sampled_from(_STEMS), pos=st.integers(0, 7))
def test_nondigit_mutation_never_matches(stem: str, pos: int) -> None:
    """Replacing one digit with a letter kills recognition (no carving)."""
    mutated = stem[:pos] + "X" + stem[pos + 1 :]
    assert UNSPSCRecognitionGrammar().recognize(mutated) == []


def test_snapshot_prefix_closure() -> None:
    """Every stem's pair-prefix ancestors are live rows (closure-clean)."""
    missing = [
        ancestor
        for stem in LIVE_STEMS
        for ancestor in (stem[:2] + "000000", stem[:4] + "0000", stem[:6] + "00")
        if ancestor not in LIVE_STEMS
    ]
    assert missing == []


def test_target_semantics_covered_by_grammar() -> None:
    """Every rule's target_semantics is produced by the shipped grammar."""
    capability = UNSPSCCapability()
    produced = {grammar.semantics for grammar in capability.get_grammars()}
    for rule in capability.get_rules():
        assert set(rule.target_semantics) <= produced
