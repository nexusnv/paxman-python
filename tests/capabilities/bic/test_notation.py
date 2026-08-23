"""Tests for BICNotation."""

from dataclasses import FrozenInstanceError

import pytest

from paxman.capabilities.BIC.notation import BICNotation

pytestmark = [pytest.mark.capability]


def test_frozen_slots_hash():
    n = BICNotation(
        bank_code="DEUT",
        country_code="DE",
        location_code="FF",
        branch_code="",
        compact="DEUTDEFF",
    )
    assert n.bank_code == "DEUT"
    assert n.country_code == "DE"
    assert n.location_code == "FF"
    assert n.branch_code == ""
    assert n.compact == "DEUTDEFF"
    assert hash(n) is not None
    assert hasattr(n, "__slots__")
    with pytest.raises(FrozenInstanceError):
        n.compact = "X"  # type: ignore[misc]


def test_compact_is_concatenation():
    n8 = BICNotation(
        bank_code="BNPA",
        country_code="FR",
        location_code="PP",
        branch_code="",
        compact="BNPAFRPP",
    )
    assert (
        n8.compact == n8.bank_code + n8.country_code + n8.location_code + n8.branch_code
    )
    assert len(n8.compact) == 8
    n11 = BICNotation(
        bank_code="DEUT",
        country_code="DE",
        location_code="FF",
        branch_code="500",
        compact="DEUTDEFF500",
    )
    assert (
        n11.compact
        == n11.bank_code + n11.country_code + n11.location_code + n11.branch_code
    )
    assert len(n11.compact) == 11


def test_branch_empty_when_8():
    n = BICNotation(
        bank_code="CHAS",
        country_code="US",
        location_code="33",
        branch_code="",
        compact="CHASUS33",
    )
    assert n.branch_code == ""
    assert len(n.compact) == 8
    n2 = BICNotation(
        bank_code="BNPA",
        country_code="FR",
        location_code="PP",
        branch_code="XXX",
        compact="BNPAFRPPXXX",
    )
    assert n2.branch_code == "XXX"
    assert len(n2.compact) == 11
