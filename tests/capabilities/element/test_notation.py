"""Tests for ElementNotation."""

from dataclasses import FrozenInstanceError

import pytest

from paxman.capabilities.Element.notation import ElementNotation

pytestmark = [pytest.mark.capability]


def test_frozen_slots_hash() -> None:
    n = ElementNotation(token="Fe", shape="symbol")
    with pytest.raises(FrozenInstanceError):
        n.token = "Cu"  # type: ignore[misc]
    with pytest.raises(FrozenInstanceError):
        n.shape = "name"  # type: ignore[misc]
    assert hasattr(ElementNotation, "__slots__")
    assert (
        len(
            {
                ElementNotation(token="Fe", shape="symbol"),
                ElementNotation(token="Fe", shape="symbol"),
                ElementNotation(token="iron", shape="name"),
            }
        )
        == 2
    )


def test_shape_token_conventions() -> None:
    symbol = ElementNotation(token="Fe", shape="symbol")
    assert symbol.token == "Fe"
    assert symbol.shape == "symbol"
    name = ElementNotation(token="iron", shape="name")
    assert name.token == "iron"
    assert name.shape == "name"
    atomic_number = ElementNotation(token="26", shape="atomic_number")
    assert atomic_number.token == "26"
    assert atomic_number.shape == "atomic_number"
    assert symbol != name
