"""Tests for MacAddress rule (scaffold)."""

import pytest

from paxman.capabilities.MacAddress.rules.ieee_ed2024 import MacAddressRule
from paxman.core.domain import RuleStrategy


@pytest.mark.capability
class TestMacAddressRule:
    """Rule: Section 1-overview (scaffold)."""

    def setup_method(self) -> None:
        self.rule = MacAddressRule()

    def test_rule_metadata(self) -> None:
        assert self.rule.name == "Section 1-overview"
        assert self.rule.strategy is RuleStrategy.REGEX
        assert self.rule.target_semantics == frozenset({"mac_address_recognition"})
        assert self.rule.requires_features == frozenset()
        assert self.rule.provenance.publication_year == 2024

    def test_matches(self) -> None:
        from paxman.capabilities.MacAddress.contract import MacAddressContract
        from paxman.capabilities.MacAddress.notation import MacAddressNotation

        contract = MacAddressContract()
        assert self.rule.matches(MacAddressNotation(value="example"), contract) is True

    def test_normalize_returns_canonical_string(self) -> None:
        from paxman.capabilities.MacAddress.contract import MacAddressContract
        from paxman.capabilities.MacAddress.notation import MacAddressNotation

        contract = MacAddressContract()
        result = self.rule.normalize(MacAddressNotation(value="example"), contract)
        assert isinstance(result, str)
        assert result == "example"
