"""Tests for the ChemicalElement capability wiring + presentation seam."""

import pytest

from paxman.capabilities.ChemicalElement.capability import ChemicalElementCapability
from paxman.capabilities.ChemicalElement.contract import ChemicalElementContract
from paxman.capabilities.ChemicalElement.notation import ChemicalElementNotation
from paxman.core.errors import ContractError

pytestmark = [pytest.mark.capability]


@pytest.fixture
def capability() -> ChemicalElementCapability:
    return ChemicalElementCapability()


@pytest.mark.capability
class TestChemicalElementCapabilityWiring:
    """Capability wiring — registry name, grammars, rules."""

    def test_registry_name(self, capability: ChemicalElementCapability) -> None:
        assert capability.name == "chemical_element"

    def test_get_grammars(self, capability: ChemicalElementCapability) -> None:
        grammars = capability.get_grammars()
        assert len(grammars) == 1
        assert {grammar.name for grammar in grammars} == {
            "chemical_element_recognition"
        }

    def test_get_rules(self, capability: ChemicalElementCapability) -> None:
        rules = capability.get_rules()
        assert len(rules) == 2
        assert {rule.name for rule in rules} == {
            "Section IR-3.1-names-and-symbols",
            "Section PTOE-element-registry",
        }

    def test_notation_frozen_slots(self) -> None:
        assert hasattr(ChemicalElementNotation, "__slots__")
        notation = ChemicalElementNotation(token="Fe", shape="symbol")
        assert notation.token == "Fe"
        assert notation.shape == "symbol"


@pytest.mark.capability
class TestChemicalElementFormatValue:
    """Presentation seam — symbol identity, name rendering, no Z branch."""

    def test_symbol_format_is_identity(
        self, capability: ChemicalElementCapability
    ) -> None:
        notation = ChemicalElementNotation(token="Fe", shape="symbol")
        assert capability.format_value("Fe", "symbol", notation) == "Fe"

    def test_default_format_is_identity(
        self, capability: ChemicalElementCapability
    ) -> None:
        notation = ChemicalElementNotation(token="Fe", shape="symbol")
        assert capability.format_value("Fe", None, notation) == "Fe"

    @pytest.mark.parametrize(
        ("symbol", "expected_name"),
        [
            ("Fe", "iron"),
            ("Al", "aluminium"),
            ("Cs", "caesium"),
            ("H", "hydrogen"),
            ("Og", "oganesson"),
            ("Au", "gold"),
            ("S", "sulfur"),
        ],
    )
    def test_name_format_renders_iupac_name(
        self, capability: ChemicalElementCapability, symbol: str, expected_name: str
    ) -> None:
        notation = ChemicalElementNotation(token=symbol, shape="symbol")
        assert capability.format_value(symbol, "name", notation) == expected_name

    def test_name_format_never_renders_alias(
        self, capability: ChemicalElementCapability
    ) -> None:
        notation = ChemicalElementNotation(token="Al", shape="symbol")
        assert capability.format_value("Al", "name", notation) != "aluminum"
        notation = ChemicalElementNotation(token="Cs", shape="symbol")
        assert capability.format_value("Cs", "name", notation) != "cesium"


@pytest.mark.capability
class TestChemicalElementCreateContract:
    """Factory — defaults resolve, unoffered formats raise ContractError."""

    def test_defaults(self) -> None:
        contract = ChemicalElementCapability.create_contract()
        assert isinstance(contract, ChemicalElementContract)
        assert contract.capability_name == "chemical_element"
        assert contract.output_format == "symbol"
        assert contract.suppress_common_words is False
        assert contract.extra_grammars == ()

    @pytest.mark.parametrize(
        ("fmt", "expected"),
        [(None, "symbol"), ("default", "symbol"), ("symbol", "symbol")],
    )
    def test_default_resolutions(self, fmt: str | None, expected: str) -> None:
        assert ChemicalElementCapability.create_contract(
            output_format=fmt
        ).output_format == (expected)

    def test_name_format_offered(self) -> None:
        contract = ChemicalElementCapability.create_contract(output_format="name")
        assert contract.output_format == "name"

    @pytest.mark.parametrize("fmt", ["atomic_number", "number", "", "SYMBOL"])
    def test_unoffered_formats_raise(self, fmt: str) -> None:
        with pytest.raises(ContractError):
            ChemicalElementCapability.create_contract(output_format=fmt)

    def test_forwards_rule_selection(self) -> None:
        contract = ChemicalElementCapability.create_contract(
            excluded_rules=["Section PTOE-element-registry"]
        )
        assert contract.excluded_rules == ("Section PTOE-element-registry",)
