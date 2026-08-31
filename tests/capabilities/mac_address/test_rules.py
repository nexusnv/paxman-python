# tests/capabilities/mac_address/test_rules.py
import pytest

from paxman.capabilities.MacAddress.contract import MacAddressContract
from paxman.capabilities.MacAddress.notation import MacAddressNotation
from paxman.capabilities.MacAddress.rules.ieee_802_ed2024 import (
    PUBLICATION,
    Section82EUIStructure,
)
from paxman.core.domain import RuleStrategy

pytestmark = [pytest.mark.capability]


def n48(hex12: str) -> MacAddressNotation:
    return MacAddressNotation(compact=hex12, shape="eui48")


def n64(hex16: str) -> MacAddressNotation:
    return MacAddressNotation(compact=hex16, shape="eui64")


class TestSection82EUIStructure:
    def setup_method(self):
        self.rule = Section82EUIStructure()
        self.contract = MacAddressContract()

    @pytest.mark.parametrize(
        "notation",
        [
            n48("001A2B3C4D5E"),
            n48("00005E005301"),
            n48("FFFFFFFFFFFF"),  # broadcast
            n48("000000000000"),  # nil
            n48("0180C2000000"),  # STP group
            n48("020000000001"),  # locally administered
            n48("333300000001"),  # IPv6 ND multicast (RFC 7042 2.3.1)
            n64("001A2B3C4D5E6677"),
            n64("02005EFFFE005301"),  # RFC 7042 modified EUI-64 shape
            n64("847127FFFE931724"),  # Zigbee ff:fe mid-address
        ],
    )
    def test_matches_valid(self, notation):
        assert self.rule.matches(notation, self.contract) is True

    @pytest.mark.parametrize(
        "notation",
        [
            MacAddressNotation(compact="001A2B3C4D5", shape="eui48"),  # 11
            MacAddressNotation(compact="001A2B3C4D5E6", shape="eui48"),  # 13
            MacAddressNotation(compact="001A2B3C4D5E66", shape="eui48"),  # 14
            MacAddressNotation(compact="001A2B3C4D5E667", shape="eui48"),  # 15
            MacAddressNotation(
                compact="001A2B3C4D5E", shape="eui64"
            ),  # shape/length disagree
            MacAddressNotation(compact="001A2B3C4D5E6677", shape="eui48"),
        ],
    )
    def test_rejects_invalid(self, notation):
        assert self.rule.matches(notation, self.contract) is False

    def test_normalize_produces_canonical(self):
        assert (
            self.rule.normalize(n48("001A2B3C4D5E"), self.contract)
            == "00:1A:2B:3C:4D:5E"
        )
        assert (
            self.rule.normalize(n64("001A2B3C4D5E6677"), self.contract)
            == "00:1A:2B:3C:4D:5E:66:77"
        )

    def test_provenance_attributes(self):
        assert PUBLICATION.authority == "IEEE"
        assert PUBLICATION.specification_name == "IEEE Std 802-2024"
        assert PUBLICATION.kind == "specification"
        assert PUBLICATION.lifecycle == "active"
        assert PUBLICATION.publication_year == 2024
        assert PUBLICATION.reference_url == "https://standards.ieee.org/ieee/802/10894"

    def test_rule_name(self):
        assert self.rule.name == "Section 8.2-eui-structure"

    def test_strategy(self):
        assert self.rule.strategy is RuleStrategy.PARSER

    def test_target_semantics(self):
        assert self.rule.target_semantics == frozenset({"mac_address_recognition"})
        assert self.rule.requires_features == frozenset()

    def test_matches_never_raises_on_garbage(self):
        # defensive: rules never raise (research 5.3)
        for bad in ("", "zz", "00:1A:2B:3C:4D:5E"):
            assert self.rule.matches(
                MacAddressNotation(compact=bad.replace(":", ""), shape="eui48"),
                self.contract,
            ) in (True, False)
