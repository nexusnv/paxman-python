# tests/capabilities/mac_address/test_capability.py
import pytest

from paxman.capabilities.MacAddress.capability import MacAddressCapability
from paxman.capabilities.MacAddress.contract import MacAddressContract
from paxman.capabilities.MacAddress.grammar import MacAddressRecognitionGrammar
from paxman.capabilities.MacAddress.notation import MacAddressNotation
from paxman.capabilities.MacAddress.rules.ieee_802_ed2024 import (
    Section82EUIStructure,
)
from paxman.core.capability import Capability

pytestmark = [pytest.mark.capability]


def m48():
    return MacAddressNotation(compact="001A2B3C4D5E", shape="eui48")


def m64():
    return MacAddressNotation(compact="001A2B3C4D5E6677", shape="eui64")


def test_is_capability_subclass():
    assert issubclass(MacAddressCapability, Capability)
    assert isinstance(MacAddressCapability(), Capability)


def test_name():
    assert MacAddressCapability.name == "mac_address"


def test_get_grammars_returns_all():
    grammars = MacAddressCapability().get_grammars()
    assert len(grammars) == 1
    assert isinstance(grammars[0], MacAddressRecognitionGrammar)
    assert grammars[0].name == "mac_address_recognition"


def test_get_rules_returns_all():
    rules = MacAddressCapability().get_rules()
    assert len(rules) == 1
    assert isinstance(rules[0], Section82EUIStructure)


def test_format_value_identity_default():
    cap = MacAddressCapability()
    assert cap.format_value("00:1A:2B:3C:4D:5E", None, m48()) == "00:1A:2B:3C:4D:5E"
    assert cap.format_value("00:1A:2B:3C:4D:5E", "colon", m48()) == "00:1A:2B:3C:4D:5E"
    assert (
        cap.format_value("00:1A:2B:3C:4D:5E", "default", m48()) == "00:1A:2B:3C:4D:5E"
    )


def test_format_value_hyphen_bare_cisco():
    cap = MacAddressCapability()
    assert cap.format_value("00:1A:2B:3C:4D:5E", "hyphen", m48()) == "00-1A-2B-3C-4D-5E"
    assert cap.format_value("00:1A:2B:3C:4D:5E", "bare", m48()) == "001A2B3C4D5E"
    assert cap.format_value("00:1A:2B:3C:4D:5E", "cisco", m48()) == "001A.2B3C.4D5E"
    assert (
        cap.format_value("00:1A:2B:3C:4D:5E:66:77", "cisco", m64())
        == "001A.2B3C.4D5E.6677"
    )


def test_format_value_eui64():
    cap = MacAddressCapability()
    assert (
        cap.format_value("00:1A:2B:3C:4D:5E", "eui64", m48())
        == "00:1A:2B:FF:FE:3C:4D:5E"
    )
    # EUI-64 input passes through unchanged (deterministic identity)
    assert (
        cap.format_value("00:1A:2B:3C:4D:5E:66:77", "eui64", m64())
        == "00:1A:2B:3C:4D:5E:66:77"
    )


def test_format_value_bit_reversed_vectors():
    cap = MacAddressCapability()
    # RFC 2469 vector
    rfc = MacAddressNotation(compact="123456789ABC", shape="eui48")
    assert (
        cap.format_value("12:34:56:78:9A:BC", "bit_reversed", rfc)
        == "48:2C:6A:1E:59:3D"
    )
    # PostgreSQL vector
    pg = MacAddressNotation(compact="08002B010203", shape="eui48")
    assert (
        cap.format_value("08:00:2B:01:02:03", "bit_reversed", pg) == "10:00:D4:80:40:C0"
    )
    # involution: swap twice returns the canonical value
    once = cap.format_value("00:1A:2B:3C:4D:5E", "bit_reversed", m48())
    assert (
        cap.format_value(
            once,
            "bit_reversed",
            MacAddressNotation(compact="0058D43CB27A", shape="eui48"),
        )
        == "00:1A:2B:3C:4D:5E"
    )


def test_create_contract_factories():
    c = MacAddressCapability.create_contract()
    assert isinstance(c, MacAddressContract)
    assert c.output_format == "colon"
    assert (
        MacAddressCapability.create_contract(output_format="hyphen").output_format
        == "hyphen"
    )
    assert MacAddressCapability.create_contract(year=2024).year == 2024
    assert MacAddressCapability.create_contract(
        extra_grammars=("some_community",)
    ).extra_grammars == ("some_community",)
