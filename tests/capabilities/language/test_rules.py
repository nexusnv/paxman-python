"""Tests for Language rule (scaffold)."""

import pytest

from paxman.capabilities.Language.rules.ietf_ed2009 import LanguageRule
from paxman.core.domain import RuleStrategy


@pytest.mark.capability
class TestLanguageRule:
    """Rule: Section 1-overview (scaffold)."""

    def setup_method(self) -> None:
        self.rule = LanguageRule()

    def test_rule_metadata(self) -> None:
        assert self.rule.name == "Section 1-overview"
        assert self.rule.strategy is RuleStrategy.REGEX
        assert self.rule.target_semantics == frozenset({"language_recognition"})
        assert self.rule.requires_features == frozenset()
        assert self.rule.provenance.publication_year == 2009

    def test_matches(self) -> None:
        from paxman.capabilities.Language.contract import LanguageContract
        from paxman.capabilities.Language.notation import LanguageNotation

        contract = LanguageContract()
        assert self.rule.matches(LanguageNotation(value="example"), contract) is True

    def test_normalize_returns_canonical_string(self) -> None:
        from paxman.capabilities.Language.contract import LanguageContract
        from paxman.capabilities.Language.notation import LanguageNotation

        contract = LanguageContract()
        result = self.rule.normalize(LanguageNotation(value="example"), contract)
        assert isinstance(result, str)
        assert result == "example"
