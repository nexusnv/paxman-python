"""Tests for DOINotation — frozen, slots, all-str fields."""

from __future__ import annotations

import dataclasses

import pytest

from paxman.capabilities.DOI.notation import DOINotation

pytestmark = [pytest.mark.capability]


class TestDOINotation:
    def test_frozen(self) -> None:
        notation = DOINotation(
            prefix="10.1038",
            suffix="nature12345",
            canonical="10.1038/nature12345",
        )
        with pytest.raises(dataclasses.FrozenInstanceError):
            notation.canonical = "x"  # type: ignore[misc]

    def test_hashable_and_eq(self) -> None:
        a = DOINotation(
            prefix="10.1038",
            suffix="nature12345",
            canonical="10.1038/nature12345",
        )
        b = DOINotation(
            prefix="10.1038",
            suffix="nature12345",
            canonical="10.1038/nature12345",
        )
        assert a == b
        assert hash(a) == hash(b)
        assert len({a, b}) == 1

    def test_slots(self) -> None:
        assert set(DOINotation.__slots__) == {
            "prefix",
            "suffix",
            "canonical",
        }
        notation = DOINotation(
            prefix="10.1038",
            suffix="nature12345",
            canonical="10.1038/nature12345",
        )
        assert not hasattr(notation, "__dict__")

    def test_all_fields_are_str(self) -> None:
        for field in dataclasses.fields(DOINotation):
            assert field.type is str, field.name

    def test_canonical_split(self) -> None:
        notation = DOINotation(
            prefix="10.1038",
            suffix="nature12345",
            canonical="10.1038/nature12345",
        )
        assert notation.prefix == "10.1038"
        assert notation.suffix == "nature12345"
        assert notation.canonical == f"{notation.prefix}/{notation.suffix}"
