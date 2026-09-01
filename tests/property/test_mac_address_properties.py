from __future__ import annotations

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

import paxman
from paxman.capabilities import MacAddress
from paxman.core.discovery import register_capability, reset_registry
from paxman.core.domain import Resolution
from paxman.core.errors import MultipleMentionsError

pytestmark = [pytest.mark.property]


def _hex_digits(n: int):
    return st.lists(st.sampled_from("0123456789ABCDEF"), min_size=n, max_size=n).map(
        "".join
    )


def _colon(compact: str) -> str:
    return ":".join(compact[i : i + 2] for i in range(0, len(compact), 2))


@pytest.fixture(autouse=True)
def _clean_registry():
    reset_registry()
    register_capability(MacAddress())
    yield
    reset_registry()


@settings(max_examples=200)
@given(st.integers(min_value=0, max_value=2**48 - 1))
def test_generated_eui48_canonicalizes_to_itself(value):
    compact = f"{value:012X}"
    contract = MacAddress.create_contract()
    result = paxman.canonicalize(_colon(compact), contract)
    assert result.status == Resolution.SUCCESS
    assert result.canonicalized_value == _colon(compact)


@settings(max_examples=200)
@given(st.integers(min_value=0, max_value=2**64 - 1))
def test_generated_eui64_canonicalizes_to_itself(value):
    compact = f"{value:016X}"
    contract = MacAddress.create_contract()
    result = paxman.canonicalize(_colon(compact), contract)
    assert result.status == Resolution.SUCCESS
    assert result.canonicalized_value == _colon(compact)


@settings(max_examples=100)
@given(_hex_digits(12))
def test_spelling_equivalence_all_families(compact):
    contract = MacAddress.create_contract()
    colon = _colon(compact)
    hyphen = colon.replace(":", "-")
    dot = ".".join(compact[i : i + 4] for i in range(0, 12, 4))
    values = {
        paxman.canonicalize(s, contract).canonicalized_value
        for s in (colon, hyphen, dot, compact.lower(), f"MAC: {colon}")
    }
    assert len(values) == 1


@settings(max_examples=100)
@given(st.text(min_size=0, max_size=64))
def test_random_strings_never_raise(text):
    contract = MacAddress.create_contract()
    try:
        result = paxman.canonicalize(text, contract)
    except MultipleMentionsError:
        return
    assert result.status in (
        Resolution.SUCCESS,
        Resolution.MISSING,
        Resolution.INVALID,
        Resolution.AMBIGUOUS,
    )


def test_bit_reversed_involution():
    from paxman.capabilities.MacAddress.capability import MacAddressCapability
    from paxman.capabilities.MacAddress.notation import MacAddressNotation

    cap = MacAddressCapability()
    for value in range(0, 256):
        octet = f"{value:02X}"
        notation = MacAddressNotation(compact=octet + "0000000000", shape="eui48")
        once = cap.format_value(f"{octet}:00:00:00:00:00", "bit_reversed", notation)
        back = cap.format_value(
            once,
            "bit_reversed",
            MacAddressNotation(compact=once.replace(":", ""), shape="eui48"),
        )
        assert back == f"{octet}:00:00:00:00:00"
