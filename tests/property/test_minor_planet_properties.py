"""Hypothesis property tests for the MinorPlanet capability.

Each property locks an invariant of recognition, validation, or
presentation using an independently derived expectation:

- an unpacked provisional built from a lane year + legal letter sets
  always canonicalizes to itself (upper, single space);
- packed renderings re-enter to the same canonical (mpc_pack/mpc_unpack
  round-trip on legal lanes);
- case-fold stability: lowercased spaced input canonicalizes identically;
- random alphanum strings never raise (INVALID-or-MISSING only).
"""

from __future__ import annotations

import pytest
from hypothesis import given
from hypothesis import strategies as st

import paxman
from paxman.capabilities import MinorPlanet
from paxman.capabilities.MinorPlanet.capability import MinorPlanetCapability
from paxman.core.discovery import register_capability, reset_registry
from paxman.core.domain import Resolution

_CAP = MinorPlanetCapability
_ = MinorPlanet  # keep required import used


@pytest.fixture(autouse=True)
def _fresh_registry() -> None:
    """Reset the registry and register MinorPlanet around each test."""

    reset_registry()
    register_capability(_CAP())
    yield
    reset_registry()


_HALF_MONTH = "ABCDEFGHJKLMNOPQRSTUVWXY"
_SECOND = "ABCDEFGHJKLMNOPQRSTUVWXYZ"


@given(
    year=st.sampled_from(["1995", "2007", "2026", "A904"]),
    hm=st.sampled_from(list(_HALF_MONTH)),
    second=st.sampled_from(list(_SECOND)),
    cycle=st.sampled_from(["", "1", "418"]),
)
def test_lane_built_provisional_self_canonicalizes(
    year: str, hm: str, second: str, cycle: str
) -> None:
    """Lane-built provisionals canonicalize to themselves."""
    text = f"{year} {hm}{second}{cycle}"
    result = paxman.canonicalize(text, _CAP.create_contract())
    assert result.status == Resolution.SUCCESS
    assert result.canonicalized_value == text


@given(
    spelled=st.sampled_from(
        ["J95X00A", "K07Tf8A", "03202", "A0345", "a0017", "~000z", "PLS2040"]
    )
)
def test_packed_spellings_reenter(spelled: str) -> None:
    """Packed spellings resolve and their canonicals re-enter exactly."""
    first = paxman.canonicalize(spelled, _CAP.create_contract())
    assert first.status == Resolution.SUCCESS
    assert first.canonicalized_value is not None
    second = paxman.canonicalize(first.canonicalized_value, _CAP.create_contract())
    assert second.status == Resolution.SUCCESS
    assert second.canonicalized_value == first.canonicalized_value


@given(text=st.sampled_from(["1995 XA", "2007 TA418", "2040 P-L", "3138 T-1", "(433)"]))
def test_case_fold_stability(text: str) -> None:
    """Lowercased spaced input canonicalizes identically."""
    upper = paxman.canonicalize(text, _CAP.create_contract())
    lower = paxman.canonicalize(text.lower(), _CAP.create_contract())
    assert upper.status == Resolution.SUCCESS
    assert lower.status == Resolution.SUCCESS
    assert lower.canonicalized_value == upper.canonicalized_value


@given(
    text=st.text(
        alphabet=st.characters(min_codepoint=32, max_codepoint=126),
        max_size=12,
    )
)
def test_random_ascii_never_raises(text: str) -> None:
    """Random ASCII never raises; verdicts are INVALID-or-MISSING-or better."""
    result = paxman.canonicalize(text, _CAP.create_contract())
    assert result.status in (
        Resolution.SUCCESS,
        Resolution.INVALID,
        Resolution.MISSING,
        Resolution.AMBIGUOUS,
    )
