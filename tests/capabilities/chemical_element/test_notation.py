"""Tests for ChemicalElementNotation."""

from dataclasses import FrozenInstanceError

import pytest

from paxman.capabilities.ChemicalElement.notation import ChemicalElementNotation

pytestmark = [pytest.mark.capability]


def test_frozen_slots_hash() -> None:
    n = ChemicalElementNotation(token="Fe", shape="symbol")
    with pytest.raises(FrozenInstanceError):
        n.token = "Cu"  # type: ignore[misc]
    with pytest.raises(FrozenInstanceError):
        n.shape = "name"  # type: ignore[misc]
    assert hasattr(ChemicalElementNotation, "__slots__")
    assert (
        len(
            {
                ChemicalElementNotation(token="Fe", shape="symbol"),
                ChemicalElementNotation(token="Fe", shape="symbol"),
                ChemicalElementNotation(token="iron", shape="name"),
            }
        )
        == 2
    )


def test_shape_token_conventions() -> None:
    symbol = ChemicalElementNotation(token="Fe", shape="symbol")
    assert symbol.token == "Fe"
    assert symbol.shape == "symbol"
    name = ChemicalElementNotation(token="iron", shape="name")
    assert name.token == "iron"
    assert name.shape == "name"
    atomic_number = ChemicalElementNotation(token="26", shape="atomic_number")
    assert atomic_number.token == "26"
    assert atomic_number.shape == "atomic_number"
    assert symbol != name
