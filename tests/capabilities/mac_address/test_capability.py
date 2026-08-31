"""Tests for the MacAddress capability wiring (scaffold)."""

import pytest

from paxman.api import canonicalize
from paxman.capabilities.MacAddress.capability import MacAddressCapability
from paxman.capabilities.MacAddress.contract import MacAddressContract
from paxman.core.discovery import register_capability, reset_registry
from paxman.core.domain import Resolution


@pytest.mark.capability
class TestMacAddressCapability:
    """Capability wiring — grammars, rules, factory."""

    def setup_method(self) -> None:
        self.capability = MacAddressCapability()

    def test_metadata(self) -> None:
        assert self.capability.name == "mac_address"

    def test_get_grammars(self) -> None:
        names = {g.name for g in self.capability.get_grammars()}
        assert names == {"mac_address_recognition"}

    def test_get_rules(self) -> None:
        names = {r.name for r in self.capability.get_rules()}
        assert names == {"Section 1-overview"}

    def test_create_contract_defaults(self) -> None:
        contract = self.capability.create_contract()
        assert isinstance(contract, MacAddressContract)
        assert contract.output_format == "colon"


@pytest.mark.capability
class TestMacAddressCapabilityPipeline:
    """End-to-end: scaffold probe resolves to MISSING."""

    @pytest.fixture(autouse=True)
    def _clean_registry(self) -> None:
        reset_registry()
        yield
        reset_registry()

    def test_scaffold_probe_missing(self) -> None:
        register_capability(MacAddressCapability())
        contract = MacAddressCapability.create_contract()
        result = canonicalize("scaffold probe", contract)
        assert result.status == Resolution.MISSING
        assert result.canonicalized_value is None
