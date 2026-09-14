"""Tests for the Timezone capability wiring (Task 7: seam + re-entry)."""

import pytest

from paxman.api import canonicalize
from paxman.capabilities.Timezone.capability import TimezoneCapability
from paxman.capabilities.Timezone.contract import TimezoneContract
from paxman.capabilities.Timezone.notation import TimezoneNotation
from paxman.core.discovery import register_capability, reset_registry
from paxman.core.domain import Resolution


@pytest.mark.capability
class TestTimezoneCapability:
    """Capability wiring — grammars, rules, factory."""

    def setup_method(self) -> None:
        self.capability = TimezoneCapability()

    def test_metadata(self) -> None:
        assert self.capability.name == "timezone"

    def test_get_grammars(self) -> None:
        names = {g.name for g in self.capability.get_grammars()}
        assert names == {
            "timezone_name_recognition",
            "timezone_abbreviation_recognition",
        }

    def test_get_rules(self) -> None:
        names = {r.name for r in self.capability.get_rules()}
        assert names == {
            "Section zone-key-membership",
            "Section link-resolution",
            "Section systemv-zones",
            "Section abbreviation-refusal",
        }

    def test_create_contract_defaults(self) -> None:
        contract = self.capability.create_contract()
        assert isinstance(contract, TimezoneContract)
        assert contract.output_format == "iana"
        assert contract.include_systemv is False
        assert contract.suppress_common_words is False
        assert contract.extra_grammars == ()

    def test_create_contract_passthrough(self) -> None:
        contract = self.capability.create_contract(
            include_systemv=True,
            suppress_common_words=True,
            extra_grammars=["first", "second"],
        )
        assert contract.include_systemv is True
        assert contract.suppress_common_words is True
        assert contract.extra_grammars == ("first", "second")

    def test_format_value_is_identity(self) -> None:
        notation = TimezoneNotation(
            key="America/New_York",
            family="name",
            compact="America/New_York",
        )
        assert (
            self.capability.format_value("America/New_York", "iana", notation)
            == "America/New_York"
        )


@pytest.mark.capability
class TestTimezoneCapabilityPipeline:
    """End-to-end: keys, links, folds, gates, re-entry."""

    @pytest.fixture(autouse=True)
    def _clean_registry(self) -> None:
        reset_registry()
        yield
        reset_registry()

    def test_scaffold_probe_missing(self) -> None:
        register_capability(TimezoneCapability())
        contract = TimezoneCapability.create_contract()
        result = canonicalize("scaffold probe", contract)
        assert result.status == Resolution.MISSING
        assert result.canonicalized_value is None

    def test_canonical_key_identity(self) -> None:
        register_capability(TimezoneCapability())
        result = canonicalize("America/New_York", TimezoneCapability.create_contract())
        assert result.status == Resolution.SUCCESS
        assert result.canonicalized_value == "America/New_York"

    def test_link_resolves_to_canonical(self) -> None:
        register_capability(TimezoneCapability())
        result = canonicalize("US/Eastern", TimezoneCapability.create_contract())
        assert result.status == Resolution.SUCCESS
        assert result.canonicalized_value == "America/New_York"

    def test_folded_mention_restores_canonical(self) -> None:
        register_capability(TimezoneCapability())
        result = canonicalize("america/new_york", TimezoneCapability.create_contract())
        assert result.status == Resolution.SUCCESS
        assert result.canonicalized_value == "America/New_York"

    def test_link_resolved_value_reenters(self) -> None:
        """US/Eastern → America/New_York → itself (ADR-0010 pin)."""
        register_capability(TimezoneCapability())
        contract = TimezoneCapability.create_contract()
        first = canonicalize("US/Eastern", contract)
        assert first.status == Resolution.SUCCESS
        value = first.canonicalized_value
        assert value == "America/New_York"
        second = canonicalize(value, contract)
        assert second.status == Resolution.SUCCESS
        assert second.canonicalized_value == value

    def test_folded_value_reenters(self) -> None:
        """america/new_york → America/New_York → itself (ADR-0010 pin)."""
        register_capability(TimezoneCapability())
        contract = TimezoneCapability.create_contract()
        first = canonicalize("america/new_york", contract)
        assert first.status == Resolution.SUCCESS
        value = first.canonicalized_value
        assert value == "America/New_York"
        second = canonicalize(value, contract)
        assert second.status == Resolution.SUCCESS
        assert second.canonicalized_value == value

    def test_systemv_default_invalid(self) -> None:
        """EST5EDT is recognized but rule-gated: INVALID by default."""
        register_capability(TimezoneCapability())
        result = canonicalize("EST5EDT", TimezoneCapability.create_contract())
        assert result.status == Resolution.INVALID
        assert result.canonicalized_value is None

    def test_systemv_flag_success_and_reentry(self) -> None:
        """EST5EDT + flag → SUCCESS EST5EDT → itself (ADR-0010 pin)."""
        register_capability(TimezoneCapability())
        contract = TimezoneCapability.create_contract(include_systemv=True)
        first = canonicalize("EST5EDT", contract)
        assert first.status == Resolution.SUCCESS
        value = first.canonicalized_value
        assert value == "EST5EDT"
        second = canonicalize(value, contract)
        assert second.status == Resolution.SUCCESS
        assert second.canonicalized_value == value

    def test_abbreviation_invalid(self) -> None:
        """Bare abbreviations are recognized but never resolved."""
        register_capability(TimezoneCapability())
        contract = TimezoneCapability.create_contract()
        for token in ("EST", "IST"):
            result = canonicalize(token, contract)
            assert result.status == Resolution.INVALID
            assert result.canonicalized_value is None
