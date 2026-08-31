"""Tests for MacAddressNotation (scaffold)."""

import dataclasses

import pytest

from paxman.capabilities.MacAddress.notation import MacAddressNotation


@pytest.mark.capability
class TestMacAddressNotation:
    """Tests for MacAddressNotation."""

    def test_value_attribute(self) -> None:
        n = MacAddressNotation(value="example")
        assert n.value == "example"

    def test_frozen(self) -> None:
        n = MacAddressNotation(value="example")
        with pytest.raises(dataclasses.FrozenInstanceError):
            n.value = "other"  # type: ignore[misc]
