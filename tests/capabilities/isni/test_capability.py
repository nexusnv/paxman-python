"""Tests for the ISNI capability wiring."""

import pytest

from paxman.api import canonicalize
from paxman.capabilities.ISNI.capability import ISNICapability
from paxman.capabilities.ISNI.contract import ISNIContract
from paxman.core.discovery import register_capability, reset_registry
from paxman.core.domain import Resolution
from paxman.core.errors import ContractError


@pytest.mark.capability
class TestISNICapability:
    """Capability wiring — grammars, rules, factory, presentation seam."""

    def setup_method(self) -> None:
        self.capability = ISNICapability()

    def test_metadata(self) -> None:
        assert self.capability.name == "isni"

    def test_get_grammars(self) -> None:
        grammars = self.capability.get_grammars()
        assert [g.name for g in grammars] == ["isni_recognition"]

    def test_get_rules(self) -> None:
        rules = self.capability.get_rules()
        assert [r.name for r in rules] == [
            "Section 4-isni-structure",
            "Section A-mod11-2-check-character",
        ]

    def test_create_contract_defaults(self) -> None:
        contract = self.capability.create_contract()
        assert isinstance(contract, ISNIContract)
        assert contract.output_format == "isni"

    def test_create_contract_rejects_unknown_format(self) -> None:
        with pytest.raises(ContractError):
            self.capability.create_contract(output_format="hyphenated")

    def test_format_value_round_trips(self) -> None:
        from paxman.capabilities.ISNI.notation import ISNINotation

        notation = ISNINotation(
            compact="0000000121032683",
            spaced="0000 0001 2103 2683",
            uri="https://isni.org/isni/0000000121032683",
            check="3",
            is_uri="false",
        )
        assert (
            self.capability.format_value("0000 0001 2103 2683", "isni", notation)
            == "0000 0001 2103 2683"
        )
        assert (
            self.capability.format_value("0000 0001 2103 2683", "compact", notation)
            == "0000000121032683"
        )
        assert (
            self.capability.format_value("0000 0001 2103 2683", "urn", notation)
            == "urn:isni:0000000121032683"
        )


@pytest.mark.capability
class TestISNICapabilityPipeline:
    """End-to-end: canonical vectors resolve through the pipeline."""

    @pytest.fixture(autouse=True)
    def _clean_registry(self) -> None:
        reset_registry()
        yield
        reset_registry()

    def test_canonical_spaced_success(self) -> None:
        register_capability(ISNICapability())
        contract = ISNICapability.create_contract()
        result = canonicalize("ISNI 0000 0001 2103 2683", contract)
        assert result.status == Resolution.SUCCESS
        assert result.canonicalized_value == "0000 0001 2103 2683"
        assert result.span == (0, 24)

    def test_compact_and_urn_reenter(self) -> None:
        register_capability(ISNICapability())
        contract = ISNICapability.create_contract()
        for text in ("0000000121032683", "urn:isni:0000000121032683"):
            result = canonicalize(text, contract)
            assert result.status == Resolution.SUCCESS
            assert result.canonicalized_value == "0000 0001 2103 2683"
