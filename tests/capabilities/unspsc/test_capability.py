"""Tests for UNSPSCCapability wiring and the presentation seam."""

import pytest

from paxman.api import canonicalize
from paxman.capabilities.UNSPSC.capability import UNSPSCCapability
from paxman.capabilities.UNSPSC.contract import UNSPSCContract
from paxman.capabilities.UNSPSC.notation import UNSPSCNotation
from paxman.core.discovery import register_capability, reset_registry
from paxman.core.domain import Resolution


@pytest.mark.capability
class TestUNSPSCCapability:
    """Capability wiring — grammars, rules, factory, format_value."""

    def setup_method(self) -> None:
        self.capability = UNSPSCCapability()

    def test_metadata(self) -> None:
        assert self.capability.name == "unspsc"

    def test_wiring_counts(self) -> None:
        grammars = self.capability.get_grammars()
        assert [g.name for g in grammars] == ["unspsc_recognition"]
        assert [r.name for r in self.capability.get_rules()] == [
            "Section 1-hierarchy-structure",
            "Section 2-level-padding",
            "Section 3-codeset-membership",
            "Section 4-business-function-suffix",
        ]

    def test_create_contract_defaults(self) -> None:
        contract = self.capability.create_contract()
        assert isinstance(contract, UNSPSCContract)
        assert contract.output_format == "unspsc"
        assert contract.include_business_function is True
        assert contract.include_live_membership is False

    @pytest.mark.parametrize(
        ("value", "output_format", "notation", "expected"),
        [
            ("43211503", None, (8, ""), "43211503"),
            ("43211503", "unspsc", (8, ""), "43211503"),
            ("43211503", "labeled", (8, ""), "UNSPSC 43211503"),
            ("43211503", "native", (8, ""), "43211503"),
            ("44121700", "native", (6, ""), "441217"),
            ("44103103", "native", (10, "14"), "4410310314"),
        ],
    )
    def test_format_value_round_trips(
        self,
        value: str,
        output_format: str | None,
        notation: tuple[int, str],
        expected: str,
    ) -> None:
        native_length, function = notation
        assert (
            self.capability.format_value(
                value,
                output_format,
                UNSPSCNotation(
                    digits=value,
                    level="commodity",
                    function=function,
                    native_length=native_length,
                ),
            )
            == expected
        )


@pytest.mark.capability
class TestUNSPSCCapabilityPipeline:
    """End-to-end smoke: label, MDM, alias, and BFI forms resolve."""

    @pytest.fixture(autouse=True)
    def _clean_registry(self) -> None:
        reset_registry()
        yield
        reset_registry()

    @pytest.mark.parametrize(
        ("text", "expected"),
        [
            ("44103103", "44103103"),
            ("UNSPSC 44103103", "44103103"),
            ("UNSPSC000.44103103", "44103103"),
            ("441217", "44121700"),
            ("4410310314", "44103103"),
            ("43000000", "43000000"),
        ],
    )
    def test_canonicalize_smoke(self, text: str, expected: str) -> None:
        register_capability(UNSPSCCapability())
        contract = UNSPSCCapability.create_contract()
        result = canonicalize(text, contract)
        assert result.status == Resolution.SUCCESS
        assert result.canonicalized_value == expected

    def test_scaffold_probe_missing(self) -> None:
        register_capability(UNSPSCCapability())
        contract = UNSPSCCapability.create_contract()
        result = canonicalize("scaffold probe", contract)
        assert result.status == Resolution.MISSING
        assert result.canonicalized_value is None
