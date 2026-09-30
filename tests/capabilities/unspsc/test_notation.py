"""Tests for UNSPSCNotation (scaffold)."""

import dataclasses

import pytest

from paxman.capabilities.UNSPSC.notation import UNSPSCNotation


@pytest.mark.capability
class TestUNSPSCNotation:
    """Tests for UNSPSCNotation."""

    def test_value_attribute(self) -> None:
        n = UNSPSCNotation(value="example")
        assert n.value == "example"

    def test_frozen(self) -> None:
        n = UNSPSCNotation(value="example")
        with pytest.raises(dataclasses.FrozenInstanceError):
            n.value = "other"  # type: ignore[misc]
