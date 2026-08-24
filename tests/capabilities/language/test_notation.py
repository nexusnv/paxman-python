"""Tests for LanguageNotation — frozen, slots, all-str fields, normalize_name."""

from __future__ import annotations

import dataclasses

import pytest

from paxman.capabilities.Language.notation import LanguageNotation, normalize_name

pytestmark = [pytest.mark.capability]


class TestLanguageNotation:
    def test_frozen(self) -> None:
        notation = LanguageNotation(
            language="en",
            extlang="",
            script="",
            region="US",
            variant="",
            extension="",
            privateuse="",
            grandfathered="",
            compact="en-US",
            raw_value="en-US",
        )
        with pytest.raises(dataclasses.FrozenInstanceError):
            notation.compact = "x"  # type: ignore[misc]

    def test_hashable_and_eq(self) -> None:
        a = LanguageNotation(
            language="en",
            extlang="",
            script="",
            region="US",
            variant="",
            extension="",
            privateuse="",
            grandfathered="",
            compact="en-US",
            raw_value="en-US",
        )
        b = LanguageNotation(
            language="en",
            extlang="",
            script="",
            region="US",
            variant="",
            extension="",
            privateuse="",
            grandfathered="",
            compact="en-US",
            raw_value="en-US",
        )
        assert a == b
        assert hash(a) == hash(b)
        assert len({a, b}) == 1

    def test_slots(self) -> None:
        params = LanguageNotation.__dataclass_params__  # type: ignore[attr-defined]
        if hasattr(params, "slots"):
            assert params.slots is True  # type: ignore[attr-defined]  # noqa: B009
        else:
            assert hasattr(LanguageNotation, "__slots__")

    def test_all_fields_are_str(self) -> None:
        for field in dataclasses.fields(LanguageNotation):
            assert field.type is str, field.name

    def test_field_values(self) -> None:
        notation = LanguageNotation(
            language="zh",
            extlang="",
            script="Hans",
            region="CN",
            variant="",
            extension="",
            privateuse="",
            grandfathered="",
            compact="zh-Hans-CN",
            raw_value="zh-Hans-CN",
        )
        assert notation.script == "Hans"
        assert notation.region == "CN"
        assert notation.compact == "zh-Hans-CN"

    def test_normalize_name(self) -> None:
        assert normalize_name("German") == "german"
        assert normalize_name("  Français  ") == "francais"
        assert normalize_name("Srpski (Serbian)") == "srpski serbian"
        assert normalize_name("Español") == "espanol"
