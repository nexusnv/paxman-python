# tests/capabilities/mac_address/test_contract.py
from dataclasses import FrozenInstanceError

import pytest

from paxman.capabilities.MacAddress.contract import MacAddressContract
from paxman.core.errors import ContractError

pytestmark = [pytest.mark.capability]


def test_defaults():
    c = MacAddressContract()
    assert c.capability_name == "mac_address"
    assert c.output_format == "colon"
    assert c.active_grammars is None
    assert c.excluded_rules == ()
    assert c.pinned_rules is None
    assert c.year is None
    assert c.extra_grammars == ()


def test_class_variables():
    assert MacAddressContract.DEFAULT_OUTPUT_FORMAT == "colon"
    assert (
        frozenset({"hyphen", "bare", "cisco", "eui64"})
        == MacAddressContract.OFFERED_OUTPUT_FORMATS
    )


@pytest.mark.parametrize(
    ("fmt", "expected"),
    [
        (None, "colon"),
        ("default", "colon"),
        ("colon", "colon"),
        ("hyphen", "hyphen"),
        ("bare", "bare"),
        ("cisco", "cisco"),
        ("eui64", "eui64"),
    ],
)
def test_output_format_resolution(fmt, expected):
    assert MacAddressContract(output_format=fmt).output_format == expected


@pytest.mark.parametrize(
    "fmt", ["unix", "", "None", "none", "eui-64", "Mac", "bit_reversed"]
)
def test_output_format_invalid_raises(fmt):
    with pytest.raises(ContractError):
        MacAddressContract(output_format=fmt)


def test_is_frozen():
    c = MacAddressContract()
    with pytest.raises(FrozenInstanceError):
        c.output_format = "hyphen"  # type: ignore[misc]
