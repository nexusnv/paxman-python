"""Tests for MinorPlanetNotation."""

import dataclasses

import pytest

from paxman.capabilities.MinorPlanet.notation import MinorPlanetNotation


@pytest.mark.capability
class TestMinorPlanetNotation:
    """Notation facets: designation + lane + spelled packed."""

    def test_frozen_slots_hash(self) -> None:
        n = MinorPlanetNotation(designation="1995 XA", form="provisional", packed="")
        assert n.designation == "1995 XA"
        assert n.form == "provisional"
        assert n.packed == ""
        assert dataclasses.is_dataclass(n)
        with pytest.raises(dataclasses.FrozenInstanceError):
            n.designation = "other"  # type: ignore[misc]
        assert hash(n) == hash(
            MinorPlanetNotation(designation="1995 XA", form="provisional", packed="")
        )

    def test_packed_empty_for_unpacked_lane(self) -> None:
        n = MinorPlanetNotation(designation="1995 XA", form="provisional", packed="")
        assert n.packed == ""

    def test_packed_preserved_case_exact(self) -> None:
        n = MinorPlanetNotation(
            designation="(360017)", form="packed_number", packed="a0017"
        )
        assert n.packed == "a0017"
