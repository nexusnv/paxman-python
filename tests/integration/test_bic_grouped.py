"""Integration guard for BIC grouped display (#41)."""

from __future__ import annotations

import pytest

from paxman.api import canonicalize
from paxman.capabilities.BIC.capability import BICCapability
from paxman.core.discovery import register_capability, reset_registry
from paxman.core.domain import Resolution

pytestmark = pytest.mark.integration


@pytest.fixture(autouse=True)
def _clean_registry():
    reset_registry()
    yield
    reset_registry()


def test_canonicalize_grouped_display() -> None:
    """(#41) canonicalize grouped must be SUCCESS, double space MISSING."""
    register_capability(BICCapability())
    c = BICCapability.create_contract()
    r = canonicalize("DEUT DE FF", c)
    assert r.status == Resolution.SUCCESS
    assert r.canonicalized_value == "DEUTDEFF"
    assert canonicalize("BNPA FR PP XXX", c).canonicalized_value == "BNPAFRPPXXX"
    assert canonicalize("DEUT  DE FF", c).status == Resolution.MISSING
    assert canonicalize("DEUT DE FF 5", c).status == Resolution.MISSING
