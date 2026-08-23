"""Tests for ORCIDNotation (scaffold)."""

import dataclasses

import pytest

from paxman.capabilities.ORCID.notation import ORCIDNotation


@pytest.mark.capability
class TestORCIDNotation:
    """Tests for ORCIDNotation."""

    def test_value_attribute(self) -> None:
        n = ORCIDNotation(value="example")
        assert n.value == "example"

    def test_frozen(self) -> None:
        n = ORCIDNotation(value="example")
        with pytest.raises(dataclasses.FrozenInstanceError):
            n.value = "other"  # type: ignore[misc]
