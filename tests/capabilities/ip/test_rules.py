"""Tests for IP validation rules."""

from __future__ import annotations

import pytest

from paxman.capabilities.IP.contract import IPContract
from paxman.capabilities.IP.notation import IPNotation
from paxman.capabilities.IP.rules.rfc_791_ed1981 import Section3Dot2IPv4Address
from paxman.capabilities.IP.rules.rfc_5952_ed2010 import (
    Section4IPv6TextRepresentation,
)
from paxman.core.domain import RuleStrategy


class TestSection3Dot2IPv4Address:
    """RFC 791 Section 3.2 — IPv4 address rule tests."""

    @pytest.mark.capability
    def test_matches_valid_ipv4(self) -> None:
        rule = Section3Dot2IPv4Address()
        contract = IPContract()
        assert rule.matches(IPNotation(address="192.168.1.1"), contract) is True

    @pytest.mark.capability
    def test_matches_loopback(self) -> None:
        rule = Section3Dot2IPv4Address()
        contract = IPContract()
        assert rule.matches(IPNotation(address="127.0.0.1"), contract) is True

    @pytest.mark.capability
    def test_matches_zeros(self) -> None:
        rule = Section3Dot2IPv4Address()
        contract = IPContract()
        assert rule.matches(IPNotation(address="0.0.0.0"), contract) is True

    @pytest.mark.capability
    def test_matches_broadcast(self) -> None:
        rule = Section3Dot2IPv4Address()
        contract = IPContract()
        assert rule.matches(IPNotation(address="255.255.255.255"), contract) is True

    @pytest.mark.capability
    def test_rejects_octet_over_255(self) -> None:
        rule = Section3Dot2IPv4Address()
        contract = IPContract()
        assert rule.matches(IPNotation(address="192.168.1.256"), contract) is False

    @pytest.mark.capability
    def test_rejects_ipv6_address(self) -> None:
        rule = Section3Dot2IPv4Address()
        contract = IPContract()
        assert (
            rule.matches(
                IPNotation(address="2001:0db8:85a3:0000:0000:8a2e:0370:7334"),
                contract,
            )
            is False
        )

    @pytest.mark.capability
    def test_rejects_non_ip_string(self) -> None:
        rule = Section3Dot2IPv4Address()
        contract = IPContract()
        assert rule.matches(IPNotation(address="not-an-ip"), contract) is False

    @pytest.mark.capability
    def test_normalize_strips_leading_zeros(self) -> None:
        rule = Section3Dot2IPv4Address()
        contract = IPContract()
        result = rule.normalize(IPNotation(address="192.168.001.001"), contract)
        assert result == "192.168.1.1"

    @pytest.mark.capability
    def test_normalize_standard_address(self) -> None:
        rule = Section3Dot2IPv4Address()
        contract = IPContract()
        result = rule.normalize(IPNotation(address="10.0.0.1"), contract)
        assert result == "10.0.0.1"

    @pytest.mark.capability
    def test_normalize_loopback(self) -> None:
        rule = Section3Dot2IPv4Address()
        contract = IPContract()
        result = rule.normalize(IPNotation(address="127.0.0.1"), contract)
        assert result == "127.0.0.1"

    @pytest.mark.capability
    def test_provenance_attributes(self) -> None:
        rule = Section3Dot2IPv4Address()
        assert rule.provenance.authority == "IETF"
        assert rule.provenance.specification_name == "RFC 791"
        assert rule.provenance.publication_year == 1981
        assert rule.provenance.lifecycle == "active"

    @pytest.mark.capability
    def test_rule_name(self) -> None:
        rule = Section3Dot2IPv4Address()
        assert rule.name == "Section 3.2-ipv4-address"

    @pytest.mark.capability
    def test_strategy_is_parser(self) -> None:
        rule = Section3Dot2IPv4Address()
        assert rule.strategy == RuleStrategy.PARSER

    @pytest.mark.capability
    def test_normalize_never_raises_on_invalid(self) -> None:
        rule = Section3Dot2IPv4Address()
        contract = IPContract()
        for bad in ["999.999.999.999", "not-an-ip", "::ffff:192", ""]:
            result = rule.normalize(IPNotation(address=bad), contract)
            assert result == bad

    @pytest.mark.capability
    def test_provenance_reference_url_is_datatracker(self) -> None:
        rule = Section3Dot2IPv4Address()
        assert rule.provenance.reference_url.startswith(
            "https://datatracker.ietf.org/doc/html/"
        )

    @pytest.mark.capability
    def test_notation_is_frozen_slots(self) -> None:
        assert IPNotation.__dataclass_params__.frozen is True
        params = IPNotation.__dict__.get("__dataclass_params__")  # type: ignore[attr-defined]
        if params is not None and hasattr(params, "slots"):
            assert getattr(params, "slots") is True  # noqa: B009
        else:
            assert hasattr(IPNotation, "__slots__")
        assert hasattr(IPNotation, "__slots__")


class TestSection4IPv6TextRepresentation:
    """RFC 5952 Section 4 — IPv6 text representation rule tests."""

    @pytest.mark.capability
    def test_matches_valid_ipv6(self) -> None:
        rule = Section4IPv6TextRepresentation()
        contract = IPContract()
        assert (
            rule.matches(
                IPNotation(address="2001:0db8:85a3:0000:0000:8a2e:0370:7334"),
                contract,
            )
            is True
        )

    @pytest.mark.capability
    def test_matches_compressed_ipv6(self) -> None:
        rule = Section4IPv6TextRepresentation()
        contract = IPContract()
        assert (
            rule.matches(IPNotation(address="2001:db8:85a3::8a2e:370:7334"), contract)
            is True
        )

    @pytest.mark.capability
    def test_matches_loopback(self) -> None:
        rule = Section4IPv6TextRepresentation()
        contract = IPContract()
        assert rule.matches(IPNotation(address="::1"), contract) is True

    @pytest.mark.capability
    def test_matches_all_zeros(self) -> None:
        rule = Section4IPv6TextRepresentation()
        contract = IPContract()
        assert rule.matches(IPNotation(address="::"), contract) is True

    @pytest.mark.capability
    def test_matches_link_local(self) -> None:
        rule = Section4IPv6TextRepresentation()
        contract = IPContract()
        assert rule.matches(IPNotation(address="fe80::1"), contract) is True

    @pytest.mark.capability
    def test_rejects_ipv4_address(self) -> None:
        rule = Section4IPv6TextRepresentation()
        contract = IPContract()
        assert rule.matches(IPNotation(address="192.168.1.1"), contract) is False

    @pytest.mark.capability
    def test_rejects_non_ip_string(self) -> None:
        rule = Section4IPv6TextRepresentation()
        contract = IPContract()
        assert rule.matches(IPNotation(address="not-an-ip"), contract) is False

    @pytest.mark.capability
    def test_normalize_compressed_form(self) -> None:
        rule = Section4IPv6TextRepresentation()
        contract = IPContract()
        result = rule.normalize(
            IPNotation(address="2001:0db8:85a3:0000:0000:8a2e:0370:7334"),
            contract,
        )
        assert result == "2001:db8:85a3::8a2e:370:7334"

    @pytest.mark.capability
    def test_normalize_loopback(self) -> None:
        rule = Section4IPv6TextRepresentation()
        contract = IPContract()
        result = rule.normalize(IPNotation(address="0:0:0:0:0:0:0:1"), contract)
        assert result == "::1"

    @pytest.mark.capability
    def test_normalize_lowercase(self) -> None:
        rule = Section4IPv6TextRepresentation()
        contract = IPContract()
        result = rule.normalize(
            IPNotation(address="2001:0DB8:85A3:0000:0000:8A2E:0370:7334"),
            contract,
        )
        assert result == "2001:db8:85a3::8a2e:370:7334"

    @pytest.mark.capability
    def test_provenance_attributes(self) -> None:
        rule = Section4IPv6TextRepresentation()
        assert rule.provenance.authority == "IETF"
        assert rule.provenance.specification_name == "RFC 5952"
        assert rule.provenance.publication_year == 2010
        assert rule.provenance.lifecycle == "active"

    @pytest.mark.capability
    def test_rule_name(self) -> None:
        rule = Section4IPv6TextRepresentation()
        assert rule.name == "Section 4-ipv6-text-representation"

    @pytest.mark.capability
    def test_strategy_is_parser(self) -> None:
        rule = Section4IPv6TextRepresentation()
        assert rule.strategy == RuleStrategy.PARSER

    @pytest.mark.capability
    def test_normalize_never_raises_on_invalid(self) -> None:
        rule = Section4IPv6TextRepresentation()
        contract = IPContract()
        for bad in ["not-an-ip", "192.168.1.1", "999.999.999.999", ""]:
            result = rule.normalize(IPNotation(address=bad), contract)
            assert result == bad

    @pytest.mark.capability
    def test_provenance_reference_url_is_datatracker(self) -> None:
        rule = Section4IPv6TextRepresentation()
        assert rule.provenance.reference_url.startswith(
            "https://datatracker.ietf.org/doc/html/"
        )
