"""Tests for PANNotation."""

from dataclasses import FrozenInstanceError

import pytest

from paxman.capabilities.CreditCard.notation import PANNotation

pytestmark = [pytest.mark.capability]


def test_frozen_slots_hash():
    n = PANNotation(digits="4111111111111111", compact="4111111111111111")
    assert n.digits == "4111111111111111"
    assert n.compact == "4111111111111111"
    assert hash(n) is not None
    assert hasattr(n, "__slots__")
    with pytest.raises(FrozenInstanceError):
        n.compact = "X"  # type: ignore[misc]


def test_digits_compact_equal():
    n = PANNotation(digits="4111111111111111", compact="4111111111111111")
    assert n.compact == n.digits
    assert isinstance(n.digits, str)
    assert isinstance(n.compact, str)
    assert len(n.digits) == 16
