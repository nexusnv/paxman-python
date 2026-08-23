"""Tests for LanguageNotation (scaffold)."""

import dataclasses

import pytest

from paxman.capabilities.Language.notation import LanguageNotation


@pytest.mark.capability
class TestLanguageNotation:
    """Tests for LanguageNotation."""

    def test_value_attribute(self) -> None:
        n = LanguageNotation(value="example")
        assert n.value == "example"

    def test_frozen(self) -> None:
        n = LanguageNotation(value="example")
        with pytest.raises(dataclasses.FrozenInstanceError):
            n.value = "other"  # type: ignore[misc]
