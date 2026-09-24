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

    def test_get_rules(self) -> None:
        names = {r.name for r in self.capability.get_rules()}
        assert names == {"Section 1-overview"}

    def test_create_contract_defaults(self) -> None:
        contract = self.capability.create_contract()
        assert isinstance(contract, DomainContract)
        assert contract.output_format == "ascii"
