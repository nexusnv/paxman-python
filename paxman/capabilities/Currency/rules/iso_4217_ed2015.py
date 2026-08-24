"""ISO 4217 alpha-3 currency code rule.

The normative code data is the current List One of the ISO 4217
Maintenance Agency (SIX Financial Information AG), cited as ISO 4217:2015
as amended by the Maintenance Agency amendment series (see D-decision 1
of the implementation plan). ISO 4217:2015 itself defines the coding
method; the code list lives with the Maintenance Agency. The data module
snapshots SIX List One, published 2026-01-01.

Note on temporal filtering: the rule's Provenance publication_year is
2015 (the edition year), but the snapshot is 2026-01-01 and includes
post-2015 codes (ZWG, VES, VED, SLE, XAD, XCG). A contract with
year=2020 still validates those codes — year filtering is coarse
(edition-year, not per-amendment). This matches the Currency
implementation plan D-decision 1 (one rule for "ISO 4217:2015 as
amended").
"""

from __future__ import annotations

from paxman.capabilities.Currency.notation import CurrencyNotation
from paxman.capabilities.Currency.rules.data.iso4217_list_one import CURRENCY_CODES
from paxman.core.contract import Contract
from paxman.core.domain import Provenance, Rule, RuleStrategy

PUBLICATION = Provenance(
    authority="ISO",
    specification_name="ISO 4217",
    kind="specification",
    reference_url="https://www.iso.org/iso-4217-currency-codes.html",
    version=None,
    lifecycle="active",
    publication_year=2015,
)


class SectionCode(Rule[CurrencyNotation]):
    """ISO 4217:2015 Section 3 — alpha-3 currency codes.

    Validates "code" shapes against the current List One as-amended (the
    full 178-code set, including the 13 codes with no minor units that
    the Money capability excludes). The grammar already folded the token
    to uppercase, so the lookup is exact.
    """

    name = "Section-code"
    strategy = RuleStrategy.LOOKUP_TABLE
    provenance = PUBLICATION
    citation = (
        "ISO 4217:2015 alpha-3 currency codes, as amended by the ISO 4217 "
        "Maintenance Agency amendment series (SIX List One, 2026-01-01)"
    )
    target_semantics = frozenset({"code_recognition"})
    requires_features = frozenset()

    def matches(self, notation: CurrencyNotation, contract: Contract) -> bool:
        """Check if the notation is a known ISO 4217 alpha-3 code.

        Args:
            notation: Currency notation to validate.
            contract: Contract configuration.

        Returns:
            True if the shape is "code" and the text is in CURRENCY_CODES.
        """
        if notation.shape != "code":
            return False
        return notation.text in CURRENCY_CODES

    def normalize(self, notation: CurrencyNotation, contract: Contract) -> str:
        """Normalize to the canonical uppercase alpha-3 code.

        Args:
            notation: Validated notation.
            contract: Contract configuration.

        Returns:
            The uppercase code (the grammar already folded the case).
        """
        return notation.text
