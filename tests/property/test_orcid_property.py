"""Property-based tests for ORCID canonicalization (hypothesis)."""

from __future__ import annotations

import pytest
from hypothesis import given
from hypothesis import strategies as st

import paxman
from paxman.capabilities.ORCID.capability import ORCIDCapability
from paxman.core.discovery import register_capability, reset_registry
from paxman.core.domain import Resolution

pytestmark = [pytest.mark.property]

_digits = st.text(alphabet="0123456789", min_size=15, max_size=15)


def _check(base15: str) -> str:
    total = 0
    for ch in base15:
        total = (total + int(ch)) * 2
    result = (12 - total % 11) % 11
    return "X" if result == 10 else str(result)


def _hyphenate(compact: str) -> str:
    return f"{compact[:4]}-{compact[4:8]}-{compact[8:12]}-{compact[12:]}"


@given(base=_digits)
def test_generated_valid_orcids_round_trip(base: str) -> None:
    compact = base + _check(base)
    hyphenated = _hyphenate(compact)
    reset_registry()
    try:
        register_capability(ORCIDCapability())
        result = paxman.canonicalize(hyphenated, ORCIDCapability.create_contract())
        assert result.status == Resolution.SUCCESS
        assert result.canonicalized_value == hyphenated
    finally:
        reset_registry()


@given(base=_digits)
def test_uri_form_equals_bare_form(base: str) -> None:
    compact = base + _check(base)
    hyphenated = _hyphenate(compact)
    reset_registry()
    try:
        register_capability(ORCIDCapability())
        bare = paxman.canonicalize(hyphenated, ORCIDCapability.create_contract())
        uri = paxman.canonicalize(
            f"https://orcid.org/{hyphenated}", ORCIDCapability.create_contract()
        )
        assert bare.status == uri.status == Resolution.SUCCESS
        assert bare.canonicalized_value == uri.canonicalized_value == hyphenated
        assert bare.span is not None and uri.span is not None
        assert uri.span[1] - uri.span[0] > bare.span[1] - bare.span[0]
    finally:
        reset_registry()
