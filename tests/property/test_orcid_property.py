"""Property-based tests for ORCID canonicalization (hypothesis)."""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from hypothesis import given
from hypothesis import strategies as st

import paxman
from paxman.capabilities.ORCID.capability import ORCIDCapability
from paxman.core.discovery import register_capability, reset_registry
from paxman.core.domain import Resolution

pytestmark = [pytest.mark.property]

_digits = st.text(alphabet="0123456789", min_size=15, max_size=15)


@pytest.fixture(autouse=True)
def _fresh_registry() -> Iterator[None]:
    """Fresh registry with ORCID registered for every hypothesis example."""
    reset_registry()
    register_capability(ORCIDCapability())
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
    assert _check("000000021825009") == "7"
    assert _check("000000021694233") == "X"
    assert _check("000000015109370") == "0"
    assert _check("142245863573047") == "6"
    assert _check("000000012281955") == "X"


def _hyphenate(compact: str) -> str:
    return f"{compact[:4]}-{compact[4:8]}-{compact[8:12]}-{compact[12:]}"


@given(base=_digits)
def test_generated_valid_orcids_round_trip(base: str) -> None:
    """Generated valid ORCID round-trips to itself."""
    compact = base + _check(base)
    hyphenated = _hyphenate(compact)
    result = paxman.canonicalize(hyphenated, ORCIDCapability.create_contract())
    assert result.status == Resolution.SUCCESS
    assert result.canonicalized_value == hyphenated


@given(base=_digits)
def test_uri_form_equals_bare_form(base: str) -> None:
    """URI form equals bare form with strictly longer span."""
    compact = base + _check(base)
    hyphenated = _hyphenate(compact)
    bare = paxman.canonicalize(hyphenated, ORCIDCapability.create_contract())
    uri = paxman.canonicalize(
        f"https://orcid.org/{hyphenated}", ORCIDCapability.create_contract()
    )
    assert bare.status == uri.status == Resolution.SUCCESS
    assert bare.canonicalized_value == uri.canonicalized_value == hyphenated
    assert bare.span is not None and uri.span is not None
    assert uri.span[1] - uri.span[0] > bare.span[1] - bare.span[0]
