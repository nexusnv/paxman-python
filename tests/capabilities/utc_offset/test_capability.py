"""Tests for the UtcOffset capability wiring (Task 7: seam + re-entry)."""

import pytest

from paxman.api import canonicalize
from paxman.capabilities.UtcOffset.capability import UtcOffsetCapability
from paxman.capabilities.UtcOffset.contract import UtcOffsetContract
from paxman.capabilities.UtcOffset.notation import UtcOffsetNotation
from paxman.core.discovery import register_capability, reset_registry
from paxman.core.domain import Resolution


@pytest.mark.capability
class TestUtcOffsetCapability:
    """Capability wiring — grammars, rules, factory."""

    def setup_method(self) -> None:
        self.capability = UtcOffsetCapability()

    def test_metadata(self) -> None:
        assert self.capability.name == "utc_offset"

    def test_get_grammars(self) -> None:
        names = {g.name for g in self.capability.get_grammars()}
        assert names == {"utc_offset_recognition"}

    def test_get_rules(self) -> None:
        names = {r.name for r in self.capability.get_rules()}
        assert names == {"Section offset-structure"}

    def test_create_contract_defaults(self) -> None:
        contract = self.capability.create_contract()
        assert isinstance(contract, UtcOffsetContract)
        assert contract.output_format == "extended"
        assert contract.suppress_common_words is False
        assert contract.extra_grammars == ()

    def test_create_contract_passthrough(self) -> None:
        contract = self.capability.create_contract(
            output_format="basic",
            suppress_common_words=True,
            extra_grammars=["first", "second"],
        )
        assert contract.output_format == "basic"
        assert contract.suppress_common_words is True
        assert contract.extra_grammars == ("first", "second")

    def test_format_value_extended_is_identity(self) -> None:
        notation = UtcOffsetNotation(compact="+05:30")
        assert self.capability.format_value("+05:30", "extended", notation) == "+05:30"

    def test_format_value_basic_strips_colon(self) -> None:
        notation = UtcOffsetNotation(compact="+05:30")
        assert self.capability.format_value("+05:30", "basic", notation) == "+0530"


@pytest.mark.capability
class TestUtcOffsetCapabilityPipeline:
    """End-to-end: forms, range bounds, basic re-entry."""

    @pytest.fixture(autouse=True)
    def _clean_registry(self) -> None:
        reset_registry()
        yield
        reset_registry()

    def test_scaffold_probe_missing(self) -> None:
        register_capability(UtcOffsetCapability())
        contract = UtcOffsetCapability.create_contract()
        result = canonicalize("scaffold probe", contract)
        assert result.status == Resolution.MISSING
        assert result.canonicalized_value is None

    def test_extended_form_identity(self) -> None:
        register_capability(UtcOffsetCapability())
        result = canonicalize("+05:30", UtcOffsetCapability.create_contract())
        assert result.status == Resolution.SUCCESS
        assert result.canonicalized_value == "+05:30"

    def test_basic_form_normalizes_to_extended(self) -> None:
        register_capability(UtcOffsetCapability())
        result = canonicalize("+0530", UtcOffsetCapability.create_contract())
        assert result.status == Resolution.SUCCESS
        assert result.canonicalized_value == "+05:30"

    def test_extended_value_reenters(self) -> None:
        """+05:30 → +05:30 → itself (ADR-0010 pin)."""
        register_capability(UtcOffsetCapability())
        contract = UtcOffsetCapability.create_contract()
        first = canonicalize("+05:30", contract)
        assert first.status == Resolution.SUCCESS
        value = first.canonicalized_value
        assert value == "+05:30"
        second = canonicalize(value, contract)
        assert second.status == Resolution.SUCCESS
        assert second.canonicalized_value == value

    def test_basic_form_reenters_through_extended(self) -> None:
        """+0530 → +05:30 → +05:30 (ADR-0010 pin, both directions)."""
        register_capability(UtcOffsetCapability())
        contract = UtcOffsetCapability.create_contract()
        first = canonicalize("+0530", contract)
        assert first.status == Resolution.SUCCESS
        value = first.canonicalized_value
        assert value == "+05:30"
        second = canonicalize(value, contract)
        assert second.status == Resolution.SUCCESS
        assert second.canonicalized_value == value

    def test_zulu_reentry(self) -> None:
        """Z → +00:00 → itself (ADR-0010 pin)."""
        register_capability(UtcOffsetCapability())
        contract = UtcOffsetCapability.create_contract()
        first = canonicalize("Z", contract)
        assert first.status == Resolution.SUCCESS
        value = first.canonicalized_value
        assert value == "+00:00"
        second = canonicalize(value, contract)
        assert second.status == Resolution.SUCCESS
        assert second.canonicalized_value == value

    def test_basic_output_format_roundtrip(self) -> None:
        """+05:30 renders +0530 under basic; the rendering re-enters."""
        register_capability(UtcOffsetCapability())
        contract = UtcOffsetCapability.create_contract(output_format="basic")
        first = canonicalize("+05:30", contract)
        assert first.status == Resolution.SUCCESS
        assert first.canonicalized_value == "+0530"
        second = canonicalize("+0530", contract)
        assert second.status == Resolution.SUCCESS
        assert second.canonicalized_value == "+0530"

    def test_real_world_bounds_accepted(self) -> None:
        """+14:00 (Kiritimati) and -12:00 (Baker Island) are valid."""
        register_capability(UtcOffsetCapability())
        contract = UtcOffsetCapability.create_contract()
        for text in ("+14:00", "-12:00"):
            result = canonicalize(text, contract)
            assert result.status == Resolution.SUCCESS
            assert result.canonicalized_value == text

    def test_beyond_real_world_bounds_rejected(self) -> None:
        """+14:30 exists nowhere: recognized shape, refused range."""
        register_capability(UtcOffsetCapability())
        contract = UtcOffsetCapability.create_contract()
        for text in ("+14:30", "-12:30"):
            result = canonicalize(text, contract)
            assert result.status == Resolution.INVALID
            assert result.canonicalized_value is None

    def test_unknown_offset_invalid(self) -> None:
        register_capability(UtcOffsetCapability())
        result = canonicalize("-00:00", UtcOffsetCapability.create_contract())
        assert result.status == Resolution.INVALID
        assert result.canonicalized_value is None
