"""Hypothesis property tests for the CreditCard capability.

Each property locks a pipeline-level invariant using an independently
derived expectation:

- a synthesized PAN (random 11–18-digit payload, leading zeros included,
  plus an independently computed Luhn MOD-10 check digit) resolves
  SUCCESS to itself (self-canonicalization over lengths 12–19, with
  deterministic anchors at both bounds);
- a random 12–19-digit run resolves SUCCESS iff an independent Luhn
  evaluation passes and INVALID otherwise — never a crash, never
  MISSING or a multi-mention error;
- space, hyphen, and 4-6-5 re-chunkings of one digit string all resolve
  to the identical compact canonical (grouping-agnostic recognition);
- the ``grouped`` rendering re-enters the default contract onto its
  compact pre-image (ADR-0011 encoding pre-image recovery);
- a leading-zero PAN canonicalizes with its leading zeros intact (no
  ``int()``-stripping anywhere in the pipeline).

Fixture-row self-canonicalization lives in
``tests/property/test_reentry_invariant.py`` ROWS; the ADR-0011 class
lives in ``tests/property/test_output_format_preservation.py``
CLASS_MAP. This module pins the fuzz-robustness half — the
``test_gtin_properties.py`` precedent.

Registry posture: the fuzz properties drive the full pipeline
(robustness cannot be observed off-pipeline), so this module uses a
local ``_fresh_registry`` fixture registering only CreditCard — the
documented ``test_money_properties.py`` exception pattern.
"""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from hypothesis import given
from hypothesis import strategies as st

from paxman.api.canonicalize import canonicalize
from paxman.capabilities.CreditCard.capability import CreditCardCapability
from paxman.core.discovery import register_capability, reset_registry
from paxman.core.domain import Resolution

pytestmark = pytest.mark.property


@pytest.fixture(autouse=True)
def _fresh_registry() -> Iterator[None]:
    """Reset the registry and register CreditCard around each test."""
    reset_registry()
    register_capability(CreditCardCapability())
    yield
    reset_registry()


def _check_digit(payload: str) -> str:
    """Luhn MOD-10 check digit (double-add-double, right-to-left).

    Derived independently — duplicates the rule's arithmetic so the
    generator cannot pass by sharing the implementation under test — and
    anchored below against the Luhn-article reference and shipped suite
    vectors. The payload occupies odd positions once the check digit is
    prepended, so payload digits at reversed index 0, 2, ... are doubled.
    """
    total = 0
    for index, digit in enumerate(reversed(payload)):
        value = ord(digit) - 48
        if index % 2 == 0:
            value *= 2
            if value > 9:
                value -= 9
        total += value
    return str((10 - total % 10) % 10)


def _luhn_valid(digits: str) -> bool:
    """Independent Luhn evaluation of a full digit string."""
    total = 0
    for index, digit in enumerate(reversed(digits)):
        value = ord(digit) - 48
        if index % 2 == 1:
            value *= 2
            if value > 9:
                value -= 9
        total += value
    return total % 10 == 0


def test_check_digit_helper_matches_known_vectors() -> None:
    """The test-local Luhn helpers agree with published vectors."""
    assert _check_digit("7992739871") == "3"  # Luhn article reference
    assert _check_digit("411111111111111") == "1"  # suite Visa 16
    assert _check_digit("01111111111") == "5"  # suite leading-zero 12
    assert _check_digit("4" + "0" * 17) == _check_digit("400000000000000000")
    assert _luhn_valid("4111111111111111")
    assert _luhn_valid("011111111115")
    assert not _luhn_valid("4111111111111112")


def _payload_strategy() -> st.SearchStrategy[str]:
    """Random 11–18-digit payload (leading zeros included).

    The length is drawn from 12–19 so the completed PAN spans the full
    floor-to-ceiling range; hypothesis exercises the integer bounds.
    """
    return st.integers(min_value=12, max_value=19).flatmap(
        lambda length: st.text(
            alphabet="0123456789", min_size=length - 1, max_size=length - 1
        )
    )


@given(payload=_payload_strategy())
def test_luhn_completed_self_canonicalization(payload: str) -> None:
    """A Luhn-completed 12–19-digit run is its own canonical value."""
    pan = payload + _check_digit(payload)
    assert 12 <= len(pan) <= 19
    result = canonicalize(pan, CreditCardCapability.create_contract())
    assert result.status is Resolution.SUCCESS
    assert result.canonicalized_value == pan


@pytest.mark.parametrize("length", [12, 19])
def test_luhn_completed_length_bounds(length: int) -> None:
    """Both length bounds (floor 12, ceiling 19) are exercised deterministically."""
    payload = "4" + "0" * (length - 2)
    pan = payload + _check_digit(payload)
    assert len(pan) == length
    assert _luhn_valid(pan)
    result = canonicalize(pan, CreditCardCapability.create_contract())
    assert result.status is Resolution.SUCCESS
    assert result.canonicalized_value == pan


@given(run=st.text(alphabet="0123456789", min_size=12, max_size=19))
def test_random_run_invalid_high_probability_no_crash(run: str) -> None:
    """Never crashes; status is decided exactly by the independent Luhn.

    Random runs fail Luhn with probability ~9/10 (the "invalid high
    probability" direction); the rare Luhn-passing draw resolves SUCCESS
    to itself — both outcomes are exact, none may raise.
    """
    result = canonicalize(run, CreditCardCapability.create_contract())
    if _luhn_valid(run):
        assert result.status is Resolution.SUCCESS
        assert result.canonicalized_value == run
    else:
        assert result.status is Resolution.INVALID
        assert result.canonicalized_value is None


def _rechunk(digits: str, sizes: tuple[int, ...], separator: str) -> str:
    """Re-chunk digits cycling the group sizes (e.g. Amex 4-6-5)."""
    groups: list[str] = []
    index = 0
    group = 0
    while index < len(digits):
        size = sizes[group % len(sizes)]
        groups.append(digits[index : index + size])
        index += size
        group += 1
    return separator.join(groups)


@given(payload=_payload_strategy())
def test_grouped_compact_equivalence(payload: str) -> None:
    """Space/hyphen/4-6-5 re-chunkings of one value share the canonical."""
    pan = payload + _check_digit(payload)
    contract = CreditCardCapability.create_contract()
    variants = (
        _rechunk(pan, (4,), " "),
        _rechunk(pan, (4,), "-"),
        _rechunk(pan, (4, 6, 5), " "),
    )
    for variant in variants:
        result = canonicalize(variant, contract)
        assert result.status is Resolution.SUCCESS, variant
        assert result.canonicalized_value == pan, variant


@given(payload=_payload_strategy())
def test_grouped_preimage_default_contract(payload: str) -> None:
    """The grouped rendering re-enters the default contract onto the compact."""
    pan = payload + _check_digit(payload)
    grouped = canonicalize(
        pan, CreditCardCapability.create_contract(output_format="grouped")
    )
    assert grouped.status is Resolution.SUCCESS
    rendered = grouped.canonicalized_value
    assert rendered is not None
    assert rendered != pan  # separator-only difference from the canonical
    back = canonicalize(rendered, CreditCardCapability.create_contract())
    assert back.status is Resolution.SUCCESS
    assert back.canonicalized_value == pan


@given(tail=st.text(alphabet="0123456789", min_size=10, max_size=17))
def test_leading_zero_luhn_invariance(tail: str) -> None:
    """Leading zeros survive the full pipeline (no ``int()``-stripping)."""
    payload = "0" + tail  # 11–18 digits, forced leading zero
    pan = payload + _check_digit(payload)  # 12–19 digits, starts with 0
    assert pan.startswith("0")
    result = canonicalize(pan, CreditCardCapability.create_contract())
    assert result.status is Resolution.SUCCESS
    assert result.canonicalized_value == pan
