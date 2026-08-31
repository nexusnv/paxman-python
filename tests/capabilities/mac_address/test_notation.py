from dataclasses import FrozenInstanceError

import pytest

from paxman.capabilities.MacAddress.notation import MacAddressNotation

pytestmark = [pytest.mark.capability]


def test_creates_with_fields():
    n = MacAddressNotation(compact="001A2B3C4D5E", shape="eui48")
    assert n.compact == "001A2B3C4D5E"
    assert n.shape == "eui48"
    n64 = MacAddressNotation(compact="001A2B3C4D5E6677", shape="eui64")
    assert n64.compact == "001A2B3C4D5E6677"
    assert n64.shape == "eui64"


def test_is_frozen():
    n = MacAddressNotation(compact="001A2B3C4D5E", shape="eui48")
    with pytest.raises(FrozenInstanceError):
        n.compact = "X"  # type: ignore[misc]
    with pytest.raises(FrozenInstanceError):
        n.shape = "eui64"  # type: ignore[misc]


def test_equality():
    assert MacAddressNotation(
        compact="001A2B3C4D5E", shape="eui48"
    ) == MacAddressNotation(compact="001A2B3C4D5E", shape="eui48")
    assert MacAddressNotation(
        compact="001A2B3C4D5E", shape="eui48"
    ) != MacAddressNotation(compact="001A2B3C4D5E6677", shape="eui64")


def test_hashable():
    s = {
        MacAddressNotation(compact="001A2B3C4D5E", shape="eui48"),
        MacAddressNotation(compact="001A2B3C4D5E", shape="eui48"),
        MacAddressNotation(compact="001A2B3C4D5E6677", shape="eui64"),
    }
    assert len(s) == 2


def test_has_slots():
    assert hasattr(MacAddressNotation, "__slots__")
