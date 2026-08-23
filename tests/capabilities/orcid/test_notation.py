"""Tests for ORCIDNotation — frozen, slots, all-str fields."""

from __future__ import annotations

import dataclasses

import pytest

from paxman.capabilities.ORCID.notation import ORCIDNotation

pytestmark = [pytest.mark.capability]


class TestORCIDNotation:
    def test_frozen(self) -> None:
        notation = ORCIDNotation(
            compact="0000000218250097",
            hyphenated="0000-0002-1825-0097",
            uri="https://orcid.org/0000-0002-1825-0097",
            check="7",
            is_uri="false",
        )
        with pytest.raises(dataclasses.FrozenInstanceError):
            notation.compact = "x"  # type: ignore[misc]

    def test_hashable_and_eq(self) -> None:
        a = ORCIDNotation(
            compact="0000000218250097",
            hyphenated="0000-0002-1825-0097",
            uri="https://orcid.org/0000-0002-1825-0097",
            check="7",
            is_uri="false",
        )
        b = ORCIDNotation(
            compact="0000000218250097",
            hyphenated="0000-0002-1825-0097",
            uri="https://orcid.org/0000-0002-1825-0097",
            check="7",
            is_uri="false",
        )
        assert a == b
        assert hash(a) == hash(b)
        assert len({a, b}) == 1

    def test_slots(self) -> None:
        assert set(ORCIDNotation.__slots__) == {
            "compact",
            "hyphenated",
            "uri",
            "check",
            "is_uri",
        }
        notation = ORCIDNotation(
            compact="0000000218250097",
            hyphenated="0000-0002-1825-0097",
            uri="https://orcid.org/0000-0002-1825-0097",
            check="7",
            is_uri="false",
        )
        assert not hasattr(notation, "__dict__")

    def test_all_fields_are_str(self) -> None:
        for field in dataclasses.fields(ORCIDNotation):
            assert field.type is str, field.name

    def test_field_values(self) -> None:
        notation = ORCIDNotation(
            compact="000000021694233X",
            hyphenated="0000-0002-1694-233X",
            uri="https://orcid.org/0000-0002-1694-233X",
            check="X",
            is_uri="true",
        )
        assert notation.check == "X"
        assert notation.is_uri == "true"
