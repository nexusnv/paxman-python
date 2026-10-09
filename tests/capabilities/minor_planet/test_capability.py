"""Tests for the MinorPlanet capability wiring."""

import pytest

from paxman.api import canonicalize
from paxman.capabilities.MinorPlanet.capability import MinorPlanetCapability
from paxman.capabilities.MinorPlanet.contract import MinorPlanetContract
from paxman.capabilities.MinorPlanet.notation import MinorPlanetNotation
from paxman.core.discovery import register_capability, reset_registry
from paxman.core.domain import Resolution
from paxman.core.errors import ContractError


@pytest.mark.capability
class TestMinorPlanetCapability:
    """Capability wiring — grammars, rules, factory."""

    def setup_method(self) -> None:
        self.capability = MinorPlanetCapability()

    def test_metadata(self) -> None:
        assert self.capability.name == "minor_planet"

    def test_get_grammars(self) -> None:
        grammars = self.capability.get_grammars()
        assert [g.name for g in grammars] == ["minor_planet_recognition"]
        assert [g.semantics for g in grammars] == ["minor_planet_recognition"]

    def test_get_rules(self) -> None:
        names = [r.name for r in self.capability.get_rules()]
        assert names == [
            "Section 1-unpacked-provisional-structure",
            "Section 2-survey-designation",
            "Section 3-packed-provisional",
            "Section 4-packed-number",
            "Section 5-permanent-number",
        ]

    def test_create_contract_defaults(self) -> None:
        contract = self.capability.create_contract()
        assert isinstance(contract, MinorPlanetContract)
        assert contract.output_format == "designation"

    def test_create_contract_packed(self) -> None:
        contract = self.capability.create_contract(output_format="packed")
        assert contract.output_format == "packed"

    def test_unknown_format_raises(self) -> None:
        with pytest.raises(ContractError):
            self.capability.create_contract(output_format="bogus")

    def test_target_semantics_covered(self) -> None:
        semantics = {g.semantics for g in self.capability.get_grammars()}
        for rule in self.capability.get_rules():
            assert set(rule.target_semantics) <= semantics

    def test_format_value_designation_identity(self) -> None:
        notation = MinorPlanetNotation(
            designation="1995 XA", form="provisional", packed=""
        )
        assert (
            self.capability.format_value("1995 XA", "designation", notation)
            == "1995 XA"
        )

    def test_format_value_packed(self) -> None:
        notation = MinorPlanetNotation(
            designation="1995 XA", form="provisional", packed=""
        )
        assert self.capability.format_value("1995 XA", "packed", notation) == "J95X00A"

    def test_format_value_packed_case_exact(self) -> None:
        notation = MinorPlanetNotation(
            designation="(360017)", form="packed_number", packed="a0017"
        )
        assert self.capability.format_value("(360017)", "packed", notation) == "a0017"

    def test_format_value_a_lane_fallback(self) -> None:
        notation = MinorPlanetNotation(
            designation="A/2017 U1", form="provisional", packed=""
        )
        assert (
            self.capability.format_value("A/2017 U1", "packed", notation) == "A/2017 U1"
        )

    def test_format_value_packed_non_20xx_extended_fallback(self) -> None:
        notation = MinorPlanetNotation(
            designation="1950 AA1000", form="provisional", packed=""
        )
        assert (
            self.capability.format_value("1950 AA1000", "packed", notation)
            == "1950 AA1000"
        )


@pytest.mark.capability
class TestMinorPlanetCapabilityPipeline:
    """End-to-end: scaffold probe resolves to MISSING."""

    @pytest.fixture(autouse=True)
    def _clean_registry(self) -> None:
        reset_registry()
        yield
        reset_registry()

    def test_scaffold_probe_missing(self) -> None:
        register_capability(MinorPlanetCapability())
        contract = MinorPlanetCapability.create_contract()
        result = canonicalize("scaffold probe", contract)
        assert result.status == Resolution.MISSING
        assert result.canonicalized_value is None

    def test_packed_format_non_20xx_extended_falls_back_and_reenters(self) -> None:
        register_capability(MinorPlanetCapability())
        packed = MinorPlanetCapability.create_contract(output_format="packed")
        result = canonicalize("1950 AA1000", packed)
        assert result.status == Resolution.SUCCESS
        assert result.canonicalized_value == "1950 AA1000"
        default = MinorPlanetCapability.create_contract()
        reentry = canonicalize("1950 AA1000", default)
        assert reentry.status == Resolution.SUCCESS
        assert reentry.canonicalized_value == "1950 AA1000"
