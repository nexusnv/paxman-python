"""Tests for ISINNotation."""

from dataclasses import FrozenInstanceError

import pytest

from paxman.capabilities.ISIN.notation import ISINNotation

pytestmark = [pytest.mark.capability]


def test_frozen_slots_hash():
    n = ISINNotation(
        country_code="US",
        nsin="037833100",
        check_digit="5",
        compact="US0378331005",
    )
    assert n.country_code == "US"
    assert n.nsin == "037833100"
    assert n.check_digit == "5"
    assert n.compact == "US0378331005"
    assert hash(n) is not None
    assert hasattr(n, "__slots__")
    with pytest.raises(FrozenInstanceError):
        n.compact = "X"  # type: ignore[misc]


def test_compact_decomposition():
    n = ISINNotation(
        country_code="US",
        nsin="037833100",
        check_digit="5",
        compact="US0378331005",
    )
    assert n.compact == n.country_code + n.nsin + n.check_digit
    assert len(n.compact) == 12
    assert len(n.country_code) == 2
    assert len(n.nsin) == 9
    assert len(n.check_digit) == 1


def test_leading_zeros_preserved():
    n = ISINNotation(
        country_code="GB",
        nsin="000263494",
        check_digit="6",
        compact="GB0002634946",
    )
    assert n.nsin == "000263494"
    assert n.compact == "GB0002634946"
    assert n.compact == n.country_code + n.nsin + n.check_digit
