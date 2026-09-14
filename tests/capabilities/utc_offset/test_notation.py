from dataclasses import FrozenInstanceError

import pytest

from paxman.capabilities.UtcOffset.notation import UtcOffsetNotation

pytestmark = [pytest.mark.capability]


def test_creates_with_fields():
    n = UtcOffsetNotation(compact="+05:30")
    assert n.compact == "+05:30"


def test_is_frozen():
    n = UtcOffsetNotation(compact="+05:30")
    with pytest.raises(FrozenInstanceError):
        n.compact = "X"  # type: ignore[misc]


def test_equality():
    assert UtcOffsetNotation(compact="+05:30") == UtcOffsetNotation(compact="+05:30")
    assert UtcOffsetNotation(compact="+05:30") != UtcOffsetNotation(compact="+00:00")


def test_hashable():
    s = {
        UtcOffsetNotation(compact="+05:30"),
        UtcOffsetNotation(compact="+05:30"),
        UtcOffsetNotation(compact="+00:00"),
    }
    assert len(s) == 2


def test_has_slots():
    assert hasattr(UtcOffsetNotation, "__slots__")
