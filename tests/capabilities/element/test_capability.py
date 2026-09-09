"""Tests for the Element capability wiring + presentation seam."""

import pytest

from paxman.capabilities.Element.capability import ElementCapability
from paxman.capabilities.Element.contract import ElementContract
from paxman.capabilities.Element.notation import ElementNotation
from paxman.core.errors import ContractError

pytestmark = [pytest.mark.capability]


@pytest.fixture
def capability() -> ElementCapability:
    return ElementCapability()


@pytest.mark.capability
class TestElementCapabilityWiring:
    """Capability wiring — registry name, grammars, rules."""

    def test_registry_name(self, capability: ElementCapability) -> None:
        assert capability.name == "element"

    def test_get_grammars(self, capability: ElementCapability) -> None:
        grammars = capability.get_grammars()
        assert len(grammars) == 1
        assert {grammar.name for grammar in grammars} == {"element_recognition"}

    def test_get_rules(self, capability: ElementCapability) -> None:
        rules = capability.get_rules()
        assert len(rules) == 2
        assert {rule.name for rule in rules} == {
            "Section IR-3.1-names-and-symbols",
            "Section PTOE-element-registry",
        }

    def test_notation_frozen_slots(self) -> None:
        assert hasattr(ElementNotation, "__slots__")
        notation = ElementNotation(token="Fe", shape="symbol")
        assert notation.token == "Fe"
        assert notation.shape == "symbol"


@pytest.mark.capability
class TestElementFormatValue:
    """Presentation seam — symbol identity, name rendering, no Z branch."""

    def test_symbol_format_is_identity(self, capability: ElementCapability) -> None:
        notation = ElementNotation(token="Fe", shape="symbol")
        assert capability.format_value("Fe", "symbol", notation) == "Fe"

    def test_default_format_is_identity(self, capability: ElementCapability) -> None:
        notation = ElementNotation(token="Fe", shape="symbol")
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
        self, capability: ElementCapability, symbol: str, expected_name: str
    ) -> None:
        notation = ElementNotation(token=symbol, shape="symbol")
        assert capability.format_value(symbol, "name", notation) == expected_name

    def test_name_format_never_renders_alias(
        self, capability: ElementCapability
    ) -> None:
        notation = ElementNotation(token="Al", shape="symbol")
        assert capability.format_value("Al", "name", notation) != "aluminum"
        notation = ElementNotation(token="Cs", shape="symbol")
        assert capability.format_value("Cs", "name", notation) != "cesium"


@pytest.mark.capability
class TestElementCreateContract:
    """Factory — defaults resolve, unoffered formats raise ContractError."""

    def test_defaults(self) -> None:
        contract = ElementCapability.create_contract()
        assert isinstance(contract, ElementContract)
        assert contract.capability_name == "element"
        assert contract.output_format == "symbol"
        assert contract.suppress_common_words is False
        assert contract.extra_grammars == ()

    @pytest.mark.parametrize(
        ("fmt", "expected"),
        [(None, "symbol"), ("default", "symbol"), ("symbol", "symbol")],
    )
    def test_default_resolutions(self, fmt: str | None, expected: str) -> None:
        assert ElementCapability.create_contract(output_format=fmt).output_format == (
            expected
        )

    def test_name_format_offered(self) -> None:
        contract = ElementCapability.create_contract(output_format="name")
        assert contract.output_format == "name"

    @pytest.mark.parametrize("fmt", ["atomic_number", "number", "", "SYMBOL"])
    def test_unoffered_formats_raise(self, fmt: str) -> None:
        with pytest.raises(ContractError):
            ElementCapability.create_contract(output_format=fmt)

    def test_forwards_rule_selection(self) -> None:
        contract = ElementCapability.create_contract(
            excluded_rules=["Section PTOE-element-registry"]
        )
        assert contract.excluded_rules == ("Section PTOE-element-registry",)
