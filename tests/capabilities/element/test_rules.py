"""Tests for the Element validation rules (Red Book 2005 + PTOE 2022)."""

import pytest

from paxman.capabilities.Element.contract import ElementContract
from paxman.capabilities.Element.notation import ElementNotation
from paxman.capabilities.Element.rules.data.periodic_table_ed2022 import (
    NAME_TO_SYMBOL,
    SYMBOLS,
    Z_TO_SYMBOL,
)
from paxman.capabilities.Element.rules.iupac_periodic_table_ed2022 import (
    SectionPtoeRegistry,
)
from paxman.capabilities.Element.rules.iupac_red_book_2005 import (
    SectionIR31NamesAndSymbols,
)
from paxman.core.domain import RuleStrategy

pytestmark = [pytest.mark.capability]

_EXTENDED_TABLE_I = (
    "as extended by the IUPAC recommendations for elements "
    "112 (2010), 114/116 (2012), 113/115/117/118 (2016)"
)


@pytest.fixture
def contract() -> ElementContract:
    return ElementContract()


@pytest.mark.capability
class TestSectionIR31NamesAndSymbols:
    """Rule: Section IR-3.1-names-and-symbols (Red Book 2005, specification)."""

    def setup_method(self) -> None:
        self.rule = SectionIR31NamesAndSymbols()

    def test_metadata(self) -> None:
        assert self.rule.name == "Section IR-3.1-names-and-symbols"
        assert self.rule.strategy is RuleStrategy.LOOKUP_TABLE
        assert self.rule.target_semantics == frozenset({"element_recognition"})
        assert self.rule.requires_features == frozenset()

    def test_provenance(self) -> None:
        provenance = self.rule.provenance
        assert provenance.authority == "IUPAC"
        assert (
            provenance.specification_name == "Nomenclature of Inorganic Chemistry "
            "(IUPAC Recommendations 2005), Chapter IR-3"
        )
        assert provenance.kind == "specification"
        assert provenance.reference_url == "https://iupac.qmul.ac.uk/RedBook2005.pdf"
        assert provenance.version == "2005"
        assert provenance.lifecycle == "active"
        assert provenance.publication_year == 2005

    def test_citation_scopes_extended_table_i(self) -> None:
        assert _EXTENDED_TABLE_I in self.rule.citation

    def test_accepts_all_symbols(self, contract: ElementContract) -> None:
        assert len(SYMBOLS) == 118
        for symbol in SYMBOLS:
            notation = ElementNotation(token=symbol, shape="symbol")
            assert self.rule.matches(notation, contract) is True

    def test_accepts_all_names(self, contract: ElementContract) -> None:
        assert len(NAME_TO_SYMBOL) == 120
        for name in NAME_TO_SYMBOL:
            notation = ElementNotation(token=name, shape="name")
            assert self.rule.matches(notation, contract) is True

    def test_aliases_normalize_to_canonical_symbol(
        self, contract: ElementContract
    ) -> None:
        assert (
            self.rule.normalize(
                ElementNotation(token="aluminum", shape="name"), contract
            )
            == "Al"
        )
        assert (
            self.rule.normalize(ElementNotation(token="cesium", shape="name"), contract)
            == "Cs"
        )

    @pytest.mark.parametrize("token", ["Xx", "D", "T", "FE", "fE", "Uut"])
    def test_rejects_non_symbols(self, contract: ElementContract, token: str) -> None:
        assert (
            self.rule.matches(ElementNotation(token=token, shape="symbol"), contract)
            is False
        )

    @pytest.mark.parametrize(
        "token", ["sulphur", "ununtrium", "ferrum", "iron oxide", ""]
    )
    def test_rejects_non_names(self, contract: ElementContract, token: str) -> None:
        assert (
            self.rule.matches(ElementNotation(token=token, shape="name"), contract)
            is False
        )

    @pytest.mark.parametrize("token", ["26", "1", "118", "Fe", "iron"])
    def test_shape_gating_rejects_atomic_number(
        self, contract: ElementContract, token: str
    ) -> None:
        assert (
            self.rule.matches(
                ElementNotation(token=token, shape="atomic_number"), contract
            )
            is False
        )

    def test_shape_gating_rejects_swapped_shapes(
        self, contract: ElementContract
    ) -> None:
        assert (
            self.rule.matches(ElementNotation(token="Fe", shape="name"), contract)
            is False
        )
        assert (
            self.rule.matches(ElementNotation(token="iron", shape="symbol"), contract)
            is False
        )

    def test_normalize_never_raises(self, contract: ElementContract) -> None:
        for token, shape in [
            ("", "symbol"),
            ("", "name"),
            ("Xx", "symbol"),
            ("sulphur", "name"),
            ("26", "atomic_number"),
        ]:
            assert isinstance(
                self.rule.normalize(
                    ElementNotation(token=token, shape=shape), contract
                ),
                str,
            )


@pytest.mark.capability
class TestSectionPtoeRegistry:
    """Rule: Section PTOE-element-registry (Periodic Table 04 May 2022)."""

    def setup_method(self) -> None:
        self.rule = SectionPtoeRegistry()

    def test_metadata(self) -> None:
        assert self.rule.name == "Section PTOE-element-registry"
        assert self.rule.strategy is RuleStrategy.LOOKUP_TABLE
        assert self.rule.target_semantics == frozenset({"element_recognition"})
        assert self.rule.requires_features == frozenset()

    def test_provenance(self) -> None:
        provenance = self.rule.provenance
        assert provenance.authority == "IUPAC"
        assert provenance.specification_name == "IUPAC Periodic Table of the Elements"
        assert provenance.kind == "registry"
        assert (
            provenance.reference_url == "https://iupac.org/wp-content/uploads/2022/07/"
            "IUPAC_Periodic_Table-04May22_CRA.pdf"
        )
        assert provenance.version == "04 May 2022"
        assert provenance.lifecycle == "active"
        assert provenance.publication_year == 2022

    def test_accepts_z_boundaries(self, contract: ElementContract) -> None:
        assert (
            self.rule.matches(
                ElementNotation(token="1", shape="atomic_number"), contract
            )
            is True
        )
        assert (
            self.rule.matches(
                ElementNotation(token="118", shape="atomic_number"), contract
            )
            is True
        )

    def test_accepts_full_z_range(self, contract: ElementContract) -> None:
        assert len(Z_TO_SYMBOL) == 118
        for z in range(1, 119):
            notation = ElementNotation(token=str(z), shape="atomic_number")
            assert self.rule.matches(notation, contract) is True

    @pytest.mark.parametrize("token", ["0", "119", "300", "1000", "-1", "abc", ""])
    def test_rejects_out_of_range_z(
        self, contract: ElementContract, token: str
    ) -> None:
        assert (
            self.rule.matches(
                ElementNotation(token=token, shape="atomic_number"), contract
            )
            is False
        )

    @pytest.mark.parametrize(
        ("token", "shape"), [("Fe", "symbol"), ("iron", "name"), ("26", "symbol")]
    )
    def test_shape_gating_rejects_symbol_and_name(
        self, contract: ElementContract, token: str, shape: str
    ) -> None:
        assert (
            self.rule.matches(ElementNotation(token=token, shape=shape), contract)
            is False
        )

    def test_normalize_maps_z_to_symbol(self, contract: ElementContract) -> None:
        assert (
            self.rule.normalize(
                ElementNotation(token="1", shape="atomic_number"), contract
            )
            == "H"
        )
        assert (
            self.rule.normalize(
                ElementNotation(token="118", shape="atomic_number"), contract
            )
            == "Og"
        )
        assert (
            self.rule.normalize(
                ElementNotation(token="026", shape="atomic_number"), contract
            )
            == "Fe"
        )

    def test_normalize_never_raises(self, contract: ElementContract) -> None:
        for token in ["0", "119", "abc", ""]:
            assert isinstance(
                self.rule.normalize(
                    ElementNotation(token=token, shape="atomic_number"), contract
                ),
                str,
            )


@pytest.mark.capability
class TestRuleNormalizeAgreement:
    """All three shapes normalize to the same canonical symbol per row."""

    def test_every_row_agrees_across_shapes(self, contract: ElementContract) -> None:
        from paxman.capabilities.Element.rules.data.periodic_table_ed2022 import (
            SYMBOL_TO_NAME,
        )

        names_and_symbols = SectionIR31NamesAndSymbols()
        registry = SectionPtoeRegistry()
        assert len(Z_TO_SYMBOL) == 118
        for z, symbol in Z_TO_SYMBOL.items():
            name = SYMBOL_TO_NAME[symbol]
            assert (
                names_and_symbols.normalize(
                    ElementNotation(token=symbol, shape="symbol"), contract
                )
                == symbol
            )
            assert (
                names_and_symbols.normalize(
                    ElementNotation(token=name, shape="name"), contract
                )
                == symbol
            )
            assert (
                registry.normalize(
                    ElementNotation(token=str(z), shape="atomic_number"), contract
                )
                == symbol
            )
