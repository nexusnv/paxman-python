"""Tests for ChemicalElementContract."""

from dataclasses import FrozenInstanceError

import pytest

from paxman.capabilities.ChemicalElement.contract import ChemicalElementContract
from paxman.core.errors import ContractError

pytestmark = [pytest.mark.capability]


def test_defaults() -> None:
    c = ChemicalElementContract()
    assert c.capability_name == "chemical_element"
    assert c.output_format == "symbol"
    assert c.suppress_common_words is False
    assert c.excluded_rules == ()
    assert c.pinned_rules is None
    assert c.year is None
    assert c.extra_grammars == ()


def test_class_variables() -> None:
    assert ChemicalElementContract.DEFAULT_OUTPUT_FORMAT == "symbol"
    assert frozenset({"name"}) == ChemicalElementContract.OFFERED_OUTPUT_FORMATS


@pytest.mark.parametrize(
    ("fmt", "expected"),
    [
        (None, "symbol"),
        ("default", "symbol"),
        ("symbol", "symbol"),
        ("name", "name"),
    ],
)
def test_output_format_resolution(fmt: str | None, expected: str) -> None:
    assert ChemicalElementContract(output_format=fmt).output_format == expected


@pytest.mark.parametrize("fmt", ["atomic_number", "number", "", "None", "SYMBOL"])
def test_output_format_invalid_raises(fmt: str) -> None:
    with pytest.raises(ContractError):
        ChemicalElementContract(output_format=fmt)


def test_is_frozen() -> None:
    c = ChemicalElementContract()
    with pytest.raises(FrozenInstanceError):
        c.output_format = "name"  # type: ignore[misc]
