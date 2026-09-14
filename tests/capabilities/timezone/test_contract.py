# tests/capabilities/timezone/test_contract.py
"""TimezoneContract configuration tests."""

from __future__ import annotations

import dataclasses

import pytest

from paxman.capabilities.Timezone.contract import TimezoneContract
from paxman.core.errors import ContractError

pytestmark = [pytest.mark.capability]


def test_defaults() -> None:
    c = TimezoneContract()
    assert c.capability_name == "timezone"
    assert c.output_format == "iana"
    assert c.include_systemv is False
    assert c.active_grammars is None
    assert c.excluded_rules == ()
    assert c.pinned_rules is None
    assert c.year is None
    assert c.extra_grammars == ()


def test_class_variables() -> None:
    assert TimezoneContract.DEFAULT_OUTPUT_FORMAT == "iana"
    assert frozenset() == TimezoneContract.OFFERED_OUTPUT_FORMATS


@pytest.mark.parametrize(
    ("fmt", "expected"),
    [
        (None, "iana"),
        ("default", "iana"),
        ("iana", "iana"),
    ],
)
def test_output_format_resolution(fmt: str | None, expected: str) -> None:
    assert TimezoneContract(output_format=fmt).output_format == expected


@pytest.mark.parametrize("fmt", ["link", "abbreviation", "basic", ""])
def test_output_format_invalid_raises(fmt: str) -> None:
    with pytest.raises(ContractError):
        TimezoneContract(output_format=fmt)


def test_include_systemv_flag_shape() -> None:
    assert TimezoneContract(include_systemv=True).include_systemv is True
    assert TimezoneContract(include_systemv=False).include_systemv is False


def test_is_frozen() -> None:
    c = TimezoneContract()
    with pytest.raises(dataclasses.FrozenInstanceError):
        c.include_systemv = True  # type: ignore[misc]
