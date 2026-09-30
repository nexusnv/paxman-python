"""Tests for UNSPSC rule (scaffold)."""

import pytest

from paxman.capabilities.UNSPSC.rules.united_nations_development_programme_ed2023 import UNSPSCRule
from paxman.core.domain import RuleStrategy


@pytest.mark.capability
class TestUNSPSCRule:
    """Rule: Section 1-overview (scaffold)."""

    def setup_method(self) -> None:
        self.rule = UNSPSCRule()

    def test_rule_metadata(self) -> None:
        assert self.rule.name == "Section 1-overview"
        assert self.rule.strategy is RuleStrategy.REGEX
        assert self.rule.target_semantics == frozenset({"unspsc_recognition"})
        assert self.rule.requires_features == frozenset()
        assert self.rule.provenance.publication_year == 2023

    def test_matches(self) -> None:
        from paxman.capabilities.UNSPSC.contract import UNSPSCContract
        from paxman.capabilities.UNSPSC.notation import UNSPSCNotation

        contract = UNSPSCContract()
        assert self.rule.matches(UNSPSCNotation(value="example"), contract) is True

    def test_normalize_returns_canonical_string(self) -> None:
        from paxman.capabilities.UNSPSC.contract import UNSPSCContract
        from paxman.capabilities.UNSPSC.notation import UNSPSCNotation

        contract = UNSPSCContract()
        result = self.rule.normalize(UNSPSCNotation(value="example"), contract)
        assert isinstance(result, str)
        assert result == "example"
