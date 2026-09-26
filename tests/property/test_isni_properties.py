"""Property-based tests for ISNI canonicalization (hypothesis)."""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from hypothesis import given
from hypothesis import strategies as st

import paxman
from paxman.capabilities.ISNI.capability import ISNICapability
from paxman.core.discovery import register_capability, reset_registry
from paxman.core.domain import Resolution

pytestmark = [pytest.mark.property]

_digits = st.text(alphabet="0123456789", min_size=15, max_size=15)


@pytest.fixture(autouse=True)
def _fresh_registry() -> Iterator[None]:
    """Fresh registry with ISNI registered for every hypothesis example."""
    reset_registry()
    register_capability(ISNICapability())
    yield
    reset_registry()


# Same formula as rules/_mod_11_2_check; anchored to fixed vectors above.
def _check(base15: str) -> str:
    total = 0
    for ch in base15:
        total = (total + int(ch)) * 2
    result = (12 - total % 11) % 11
    return "X" if result == 10 else str(result)


def test_check_matches_hand_verified_vectors() -> None:
    """Anchor _check to independently computed vectors (not production code)."""
    assert _check("000000012103268") == "3"
    assert _check("000000012281955") == "X"
    assert _check("000000012146438") == "X"
    assert _check("000000012124196") == "0"
    assert _check("000000012297470") == "1"


def _spaced(compact: str) -> str:
    return f"{compact[:4]} {compact[4:8]} {compact[8:12]} {compact[12:]}"


@given(base=_digits)
def test_generated_valid_isnis_round_trip(base: str) -> None:
    """Generated valid ISNI round-trips to itself."""
    compact = base + _check(base)
    spaced = _spaced(compact)
    result = paxman.canonicalize(spaced, ISNICapability.create_contract())
    assert result.status == Resolution.SUCCESS
    assert result.canonicalized_value == spaced


@given(base=_digits)
def test_generated_compact_and_urn_reenter(base: str) -> None:
    """Generated compact and urn:isni: spellings resolve to spaced."""
    compact = base + _check(base)
    expected = _spaced(compact)
    for text in (compact, f"urn:isni:{compact}"):
        result = paxman.canonicalize(text, ISNICapability.create_contract())
        assert result.status == Resolution.SUCCESS
        assert result.canonicalized_value == expected
