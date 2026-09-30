"""Tests for UNSPSCNotation."""

import dataclasses

import pytest

from paxman.capabilities.UNSPSC.notation import UNSPSCNotation


@pytest.mark.capability
class TestUNSPSCNotation:
    """UNSPSC notation carries the 8-digit stem plus level/function facets."""

    def test_field_invariants(self) -> None:
        n = UNSPSCNotation(
            digits="43211503", level="commodity", function="", native_length=8
        )
        assert n.digits == "43211503"
        assert n.level == "commodity"
        assert n.function == ""
        assert n.native_length == 8
        assert len(n.digits) == 8

    def test_frozen_slots_hashable(self) -> None:
        n = UNSPSCNotation(
            digits="43211503", level="commodity", function="", native_length=8
        )
        with pytest.raises(dataclasses.FrozenInstanceError):
            n.digits = "other"  # type: ignore[misc]
        assert hasattr(n, "__slots__")
        assert hash(n) == hash(
            UNSPSCNotation(
                digits="43211503", level="commodity", function="", native_length=8
            )
        )

    def test_level_derivation(self) -> None:
        cases = {
            "43000000": "segment",
            "43210000": "family",
            "43211500": "class",
            "43211503": "commodity",
        }
        for digits, level in cases.items():
            n = UNSPSCNotation(
                digits=digits, level=level, function="", native_length=8
            )
            assert n.level == level

    def test_native_length_lane(self) -> None:
        alias = UNSPSCNotation(
            digits="44121700", level="class", function="", native_length=6
        )
        assert alias.native_length == 6
        assert alias.digits == "44121700"
        bfi = UNSPSCNotation(
            digits="44103103", level="commodity", function="14", native_length=10
        )
        assert bfi.native_length == 10
        assert bfi.function == "14"
