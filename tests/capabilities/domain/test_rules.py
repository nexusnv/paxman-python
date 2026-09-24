"""Tests for the RFC 1034 name-syntax rule (scaffold)."""

import pytest

from paxman.capabilities.Domain.rules.rfc_1034_name_syntax import Rfc1034NameSyntax
from paxman.core.domain import RuleStrategy


@pytest.mark.capability
class TestRfc1034NameSyntax:
    """Rule: Section 1-overview (scaffold)."""

    def setup_method(self) -> None:
        self.rule = Rfc1034NameSyntax()

    def test_rule_metadata(self) -> None:
        assert self.rule.name == "Section 1-overview"
        assert self.rule.strategy is RuleStrategy.REGEX
        assert self.rule.target_semantics == frozenset({"ascii_hostname"})
        assert self.rule.requires_features == frozenset()
        assert self.rule.provenance.publication_year == 1987

    def test_matches(self) -> None:
        from paxman.capabilities.Domain.contract import DomainContract
        from paxman.capabilities.Domain.notation import DomainNotation

        contract = DomainContract()
        notation = DomainNotation(raw="example", labels=("example",), tld="example")
        assert self.rule.matches(notation, contract) is True
