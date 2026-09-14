from dataclasses import FrozenInstanceError

import pytest

from paxman.capabilities.Timezone.notation import TimezoneNotation

pytestmark = [pytest.mark.capability]


def test_creates_with_fields():
    n = TimezoneNotation(
        key="America/New_York", family="name", compact="America/New_York"
    )
    assert n.key == "America/New_York"
    assert n.family == "name"
    assert n.compact == "America/New_York"
    abbr = TimezoneNotation(key="EST", family="abbreviation", compact="EST")
    assert abbr.key == "EST"
    assert abbr.family == "abbreviation"
    assert abbr.compact == "EST"


def test_is_frozen():
    n = TimezoneNotation(
        key="America/New_York", family="name", compact="America/New_York"
    )
    with pytest.raises(FrozenInstanceError):
        n.key = "X"  # type: ignore[misc]
    with pytest.raises(FrozenInstanceError):
        n.family = "abbreviation"  # type: ignore[misc]
    with pytest.raises(FrozenInstanceError):
        n.compact = "X"  # type: ignore[misc]


def test_equality():
    assert TimezoneNotation(
        key="America/New_York", family="name", compact="America/New_York"
    ) == TimezoneNotation(
        key="America/New_York", family="name", compact="America/New_York"
    )
    assert TimezoneNotation(
        key="America/New_York", family="name", compact="America/New_York"
    ) != TimezoneNotation(key="EST", family="abbreviation", compact="EST")


def test_hashable():
    s = {
        TimezoneNotation(
            key="America/New_York", family="name", compact="America/New_York"
        ),
        TimezoneNotation(
            key="America/New_York", family="name", compact="America/New_York"
        ),
        TimezoneNotation(key="EST", family="abbreviation", compact="EST"),
    }
    assert len(s) == 2


def test_has_slots():
    assert hasattr(TimezoneNotation, "__slots__")
