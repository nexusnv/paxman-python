# tests/capabilities/utc_offset/test_contract.py
"""UtcOffsetContract configuration tests."""

from __future__ import annotations

import dataclasses

import pytest

from paxman.capabilities.UtcOffset.contract import UtcOffsetContract
from paxman.core.errors import ContractError

pytestmark = [pytest.mark.capability]


def test_defaults() -> None:
    c = UtcOffsetContract()
    assert c.capability_name == "utc_offset"
    assert c.output_format == "extended"
    assert c.active_grammars is None
    assert c.excluded_rules == ()
    assert c.pinned_rules is None
    assert c.year is None
    assert c.extra_grammars == ()


def test_class_variables() -> None:
    assert UtcOffsetContract.DEFAULT_OUTPUT_FORMAT == "extended"
    assert frozenset({"basic"}) == UtcOffsetContract.OFFERED_OUTPUT_FORMATS


@pytest.mark.parametrize(
    ("fmt", "expected"),
    [
        (None, "extended"),
        ("default", "extended"),
        ("extended", "extended"),
        ("basic", "basic"),
    ],
)
def test_output_format_resolution(fmt: str | None, expected: str) -> None:
    assert UtcOffsetContract(output_format=fmt).output_format == expected


@pytest.mark.parametrize("fmt", ["abbreviation", "link", "iana", ""])
def test_output_format_invalid_raises(fmt: str) -> None:
    with pytest.raises(ContractError):
        UtcOffsetContract(output_format=fmt)


def test_is_frozen() -> None:
    c = UtcOffsetContract()
    with pytest.raises(dataclasses.FrozenInstanceError):
        c.output_format = "basic"  # type: ignore[misc]
