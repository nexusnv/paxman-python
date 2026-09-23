"""Tests for GTINNotation."""

import dataclasses

import pytest

from paxman.capabilities.GTIN.notation import GTINNotation


@pytest.mark.capability
class TestGTINNotation:
    def test_frozen_slots_hash(self) -> None:
        n = GTINNotation(digits="614141999996", native_length=12, has_ai=False)
        assert n.digits == "614141999996"
        with pytest.raises(dataclasses.FrozenInstanceError):
            n.digits = "other"  # type: ignore[misc]
        assert "__dict__" not in dir(n)
        assert hash(n) == hash(GTINNotation("614141999996", 12, False))

    def test_facet_shape(self) -> None:
        n = GTINNotation("614141999996", 12, False)
        assert n.native_length == len(n.digits)
        assert n.has_ai is False
        ai = GTINNotation("03453120000011", 14, True)
        assert ai.has_ai is True
        assert ai.native_length == 14
