"""Tests for ORCID rule (scaffold)."""

import pytest

from paxman.capabilities.ORCID.rules.iso_27729_ed2024 import ORCIDRule
from paxman.core.domain import RuleStrategy


@pytest.mark.capability
class TestORCIDRule:
    """Rule: Section 1-overview (scaffold)."""

    def setup_method(self) -> None:
        self.rule = ORCIDRule()

    def test_rule_metadata(self) -> None:
        assert self.rule.name == "Section 1-overview"
        assert self.rule.strategy is RuleStrategy.REGEX
        assert self.rule.target_semantics == frozenset({"orcid_recognition"})
        assert self.rule.requires_features == frozenset()
        assert self.rule.provenance.publication_year == 2024

    def test_matches(self) -> None:
        from paxman.capabilities.ORCID.contract import ORCIDContract
        from paxman.capabilities.ORCID.notation import ORCIDNotation

        contract = ORCIDContract()
        assert self.rule.matches(ORCIDNotation(value="example"), contract) is True

    def test_normalize_returns_canonical_string(self) -> None:
        from paxman.capabilities.ORCID.contract import ORCIDContract
        from paxman.capabilities.ORCID.notation import ORCIDNotation

        contract = ORCIDContract()
        result = self.rule.normalize(ORCIDNotation(value="example"), contract)
        assert isinstance(result, str)
        assert result == "example"
