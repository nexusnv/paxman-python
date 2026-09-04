"""IUPAC Periodic Table of the Elements (04 May 2022) registry rule.

Validates ``atomic_number`` shapes: the token must be a bare integer in
1-118 and resolves to the canonical proper-case symbol via the registry
snapshot in ``rules/data/periodic_table_ed2022.py``.
"""

from __future__ import annotations

from paxman.capabilities.Element.notation import ElementNotation
from paxman.capabilities.Element.rules.data.periodic_table_ed2022 import (
    Z_TO_SYMBOL,
)
from paxman.core.contract import Contract
from paxman.core.domain import Provenance, Rule, RuleStrategy

PUBLICATION = Provenance(
    authority="IUPAC",
    specification_name="IUPAC Periodic Table of the Elements",
    kind="registry",
    reference_url=(
        "https://iupac.org/wp-content/uploads/2022/07/"
        "IUPAC_Periodic_Table-04May22_CRA.pdf"
    ),
    version="04 May 2022",
    lifecycle="active",
    publication_year=2022,
)


class SectionPtoeRegistry(Rule[ElementNotation]):
    """Periodic Table registry — atomic numbers 1-118 to symbols."""

    name = "Section PTOE-element-registry"
    strategy = RuleStrategy.LOOKUP_TABLE
    provenance = PUBLICATION
    citation = (
        "IUPAC Periodic Table of the Elements, 04 May 2022 release "
        "(118 elements, Z 1-118), Table I names and symbols as extended by "
        "the IUPAC recommendations for elements 112 (2010), 114/116 (2012), "
        "113/115/117/118 (2016)"
    )
    target_semantics = frozenset({"element_recognition"})
    requires_features = frozenset()

    @staticmethod
    def _parse_z(token: str) -> int | None:
        """Return the atomic number for a digits token, else None."""
        try:
            z = int(token)
        except (TypeError, ValueError):
            return None
        if 1 <= z <= 118:
            return z
        return None

    def matches(self, notation: ElementNotation, contract: Contract) -> bool:
        """Check if the notation is an in-range atomic number.

        Args:
            notation: Element notation to validate.
            contract: Contract configuration.

        Returns:
            True if the shape is "atomic_number" and the token parses to
            an integer in 1-118.
        """
        if notation.shape != "atomic_number":
            return False
        return self._parse_z(notation.token) is not None

    def normalize(self, notation: ElementNotation, contract: Contract) -> str:
        """Normalize to the canonical proper-case IUPAC symbol.

        Args:
            notation: Validated notation.
            contract: Contract configuration.

        Returns:
            The registry symbol for the atomic number; the input token
            unchanged when it does not parse to an in-range integer.
        """
        z = self._parse_z(notation.token)
        if z is None:
            return notation.token
        return Z_TO_SYMBOL[z]
