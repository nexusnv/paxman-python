"""Tests for the Domain capability wiring (scaffold)."""

import pytest

from paxman.capabilities.Domain.capability import DomainCapability
from paxman.capabilities.Domain.contract import DomainContract


@pytest.mark.capability
class TestDomainCapability:
    """Capability wiring — grammars, rules, factory."""

    def setup_method(self) -> None:
        self.capability = DomainCapability()

    def test_metadata(self) -> None:
        assert self.capability.name == "domain"

    def test_get_grammars(self) -> None:
        names = {g.name for g in self.capability.get_grammars()}
        assert names == {"ascii_hostname"}

    def test_get_rules_returns_five(self) -> None:
        names = [r.name for r in self.capability.get_rules()]
        assert names == [
            "Section-3.1-name-syntax",
            "Section-2.3.4-label-length",
            "UTS46-statuses",
            "Section-2-bidi-context",
            "root-zone-membership",
        ]

    def test_create_contract_defaults(self) -> None:
        contract = self.capability.create_contract()
        assert isinstance(contract, DomainContract)
        assert contract.output_format == "ascii"


@pytest.mark.capability
class TestDomainLookupStructure:
    """ADR-0012 structural pins — read get_rules() directly, no registry."""

    def test_exactly_one_lookup_table_rule(self) -> None:
        from paxman.capabilities.Domain.rules.iana_root_zone_membership import (
            IanaRootZoneMembership,
        )
        from paxman.core.domain import RuleStrategy

        rules = DomainCapability().get_rules()
        lookups = [r for r in rules if r.strategy is RuleStrategy.LOOKUP_TABLE]
        assert len(lookups) == 1
        assert isinstance(lookups[0], IanaRootZoneMembership)

    def test_lookup_rule_always_applied_by_default(self) -> None:
        from paxman.capabilities.Domain.capability import DomainCapability

        contract = DomainCapability.create_contract()
        assert "root-zone-membership" not in contract.excluded_rules
        assert contract.pinned_rules is None
        for rule in DomainCapability().get_rules():
            if rule.name == "root-zone-membership":
                assert rule.requires_features == frozenset()
