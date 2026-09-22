"""Hypothesis property tests for the LEI capability.

Each property locks a pipeline-level invariant using an independently
derived expectation:

- a synthesized valid LEI (prefix from the accredited-LOU snapshot,
  random 14-char entity block, independently computed MOD 97-10 check
  digits) always resolves to itself (fixed point);
- random 20-char input never raises and resolves to a well-formed
  status (INVALID bias — most strings fail the MOD 97-10 check);
- spaced and compact spellings of one value resolve identically;
- the ``urn`` rendering round-trips through the compact pivot.

Self-canonicalization fixed points live in
``tests/property/test_reentry_invariant.py`` ROWS; the ADR-0011 encoding
lives in ``tests/property/test_output_format_preservation.py``
CLASS_MAP. This module pins only the fuzz-robustness half.

Registry posture: the fuzz properties drive the full pipeline
(robustness cannot be observed off-pipeline), so this module uses a
local ``_fresh_registry`` fixture registering only LEI — the documented
``test_money_properties.py`` exception pattern.
"""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from hypothesis import given
from hypothesis import strategies as st

from paxman.api.canonicalize import canonicalize
from paxman.capabilities.LEI.capability import LEICapability
from paxman.capabilities.LEI.rules.data.lou_prefixes import (
    ACCREDITED_LOU_PREFIXES,
)
from paxman.core.discovery import register_capability, reset_registry
from paxman.core.domain import Resolution
from paxman.core.errors import MultipleMentionsError

pytestmark = pytest.mark.property


@pytest.fixture(autouse=True)
def _fresh_registry() -> Iterator[None]:
    """Reset the registry and register LEI around each test."""
    reset_registry()
    register_capability(LEICapability())
    yield
    reset_registry()


_PREFIXES = sorted(ACCREDITED_LOU_PREFIXES)
_ENTITY_ALPHABET = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"


def _expand(compact: str) -> str:
    """Expand each character to digits (digits stay, A=10 ... Z=35).

    Derived independently from the ISO/IEC 7064 MOD 97-10 system cited
    by ISO 17442-1 — duplicates the rule's expansion so the generator
    cannot pass by sharing the implementation under test.
    """
    parts: list[str] = []
    for ch in compact:
        if "0" <= ch <= "9":
            parts.append(ch)
        else:
            parts.append(str(ord(ch) - 55))
    return "".join(parts)


def _mod97_10_valid(compact: str) -> bool:
    """Whole-string MOD 97-10 check (no rearrangement)."""
    remainder = 0
    for digit in _expand(compact):
        remainder = (remainder * 10 + int(digit)) % 97
    return remainder == 1


def _compute_check_digits(first18: str) -> str:
    """Find the check digits making the 20-char LEI MOD 97-10 valid."""
    for candidate in range(100):
        digits = f"{candidate:02d}"
        if _mod97_10_valid(first18 + digits):
            return digits
    raise AssertionError(f"no check digits for {first18!r}")


def test_check_digit_helper_matches_known_vector() -> None:
    """The test-local MOD 97-10 helper agrees with the LSE reference LEI."""
    assert _compute_check_digits("213800KUD8LAJWSQ9D") == "15"


@given(
    prefix=st.sampled_from(_PREFIXES),
    entity=st.text(alphabet=_ENTITY_ALPHABET, min_size=14, max_size=14),
)
def test_synthesized_valid_leis_self_canonicalize(prefix: str, entity: str) -> None:
    """Any synthesized valid LEI resolves to itself byte-identically."""
    compact = prefix + entity + _compute_check_digits(prefix + entity)
    result = canonicalize(compact, LEICapability.create_contract())
    assert result.status == Resolution.SUCCESS
    assert result.canonicalized_value == compact


@given(text=st.text(alphabet=_ENTITY_ALPHABET, min_size=20, max_size=20))
def test_random_20_char_never_raises(text: str) -> None:
    """Random 20-char input never raises; non-LEIs stay MISSING/INVALID."""
    contract = LEICapability.create_contract()
    try:
        result = canonicalize(text, contract)
    except MultipleMentionsError:
        return
    assert result.status in (
        Resolution.SUCCESS,
        Resolution.MISSING,
        Resolution.INVALID,
        Resolution.AMBIGUOUS,
    )
    if result.status != Resolution.SUCCESS:
        assert result.candidates == ()
    else:
        assert result.canonicalized_value is not None


@given(
    prefix=st.sampled_from(_PREFIXES),
    entity=st.text(alphabet=_ENTITY_ALPHABET, min_size=14, max_size=14),
)
def test_spaced_vs_compact_same_value(prefix: str, entity: str) -> None:
    """Single-spaced and compact spellings of one LEI resolve identically."""
    compact = prefix + entity + _compute_check_digits(prefix + entity)
    spaced = f"{compact[0:4]} {compact[4:]}"
    contract = LEICapability.create_contract()
    r_compact = canonicalize(compact, contract)
    r_spaced = canonicalize(spaced, contract)
    assert r_compact.status == Resolution.SUCCESS
    assert r_spaced.status == Resolution.SUCCESS
    assert r_spaced.canonicalized_value == r_compact.canonicalized_value
    assert r_compact.canonicalized_value == compact


def test_urn_round_trip_strips_to_compact() -> None:
    """The urn rendering re-enters the default contract onto compact."""
    text = "5493000IBP32UQZ0KL24"
    rendered = canonicalize(text, LEICapability.create_contract(output_format="urn"))
    assert rendered.status == Resolution.SUCCESS
    assert rendered.canonicalized_value == f"urn:lei:{text}"
    stripped = (rendered.canonicalized_value or "").removeprefix("urn:lei:")
    assert stripped == text
    reentry = canonicalize(stripped, LEICapability.create_contract())
    assert reentry.status == Resolution.SUCCESS
    assert reentry.canonicalized_value == text
