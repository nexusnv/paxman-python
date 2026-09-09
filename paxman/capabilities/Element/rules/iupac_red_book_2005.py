"""IUPAC Red Book 2005 (Chapter IR-3) element names/symbols rule.

Validates ``symbol`` and ``name`` shapes against the 118-entry registry
snapshot in ``rules/data/periodic_table_ed2022.py``. The Red Book Table I
itself lists elements 1-111; the shipped tables extend it with the
subsequently named elements, per the rule citation.
"""

from __future__ import annotations

from paxman.capabilities.Element.notation import ElementNotation
from paxman.capabilities.Element.rules.data.periodic_table_ed2022 import (
    NAME_TO_SYMBOL,
    SYMBOLS,
)
from paxman.core.contract import Contract
from paxman.core.domain import Provenance, Rule, RuleStrategy

PUBLICATION = Provenance(
    authority="IUPAC",
    specification_name=(
        "Nomenclature of Inorganic Chemistry (IUPAC Recommendations 2005), Chapter IR-3"
    ),
    kind="specification",
    reference_url="https://iupac.qmul.ac.uk/RedBook2005.pdf",
    version="2005",
    lifecycle="active",
    publication_year=2005,
)


class SectionIR31NamesAndSymbols(Rule[ElementNotation]):
    """Red Book Section IR-3.1 — names and symbols of the elements.

    Validates ``symbol`` shapes against the 118-symbol set and ``name``
    shapes against the 120-entry name map (118 IUPAC lowercase names plus
    the Table I footnoted alternatives ``aluminum`` and ``cesium``).
    """

    name = "Section IR-3.1-names-and-symbols"
    strategy = RuleStrategy.LOOKUP_TABLE
    provenance = PUBLICATION
    citation = (
        "Nomenclature of Inorganic Chemistry (IUPAC Recommendations 2005), "
        "Chapter IR-3, Table I (elements 1-111), as extended by the IUPAC "
        "recommendations for elements 112 (2010), 114/116 (2012), "
        "113/115/117/118 (2016)"
    )
    target_semantics = frozenset({"element_recognition"})
    requires_features = frozenset()

    def matches(self, notation: ElementNotation, contract: Contract) -> bool:
        """Check if the notation is a known element symbol or name.

        Args:
            notation: Element notation to validate.
            contract: Contract configuration.

        Returns:
            True if the shape is "symbol" and the token is in SYMBOLS, or
            the shape is "name" and the token is in NAME_TO_SYMBOL.
        """
        if notation.shape == "symbol":
            return notation.token in SYMBOLS
        if notation.shape == "name":
            return notation.token in NAME_TO_SYMBOL
        return False

    def normalize(self, notation: ElementNotation, contract: Contract) -> str:
        """Normalize to the canonical proper-case IUPAC symbol.

        Args:
            notation: Validated notation.
            contract: Contract configuration.

        Returns:
            The canonical symbol; the input token unchanged when the
            notation is not a known symbol or name.
        """
        if notation.shape == "symbol" and notation.token in SYMBOLS:
            return notation.token
        if notation.shape == "name":
            symbol = NAME_TO_SYMBOL.get(notation.token)
            if symbol is not None:
                return symbol
        return notation.token
