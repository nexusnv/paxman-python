"""ISO 3166-3:2020 formerly used country names validation rule.

Validates that a recognized notation corresponds to a formerly used
country name per ISO 3166-3. The canonical value is the historical
entity's own former alpha-2 code (e.g., "SU" for USSR), NOT a successor
state's code.

SectionHistoricalNames accepts the following input shapes for round-trip
support:
- shape="name":   Validates the name against FORMER_NAME_TO_ALPHA2_NORMALIZED
- shape="alpha2": Validates the code against FORMER_ALPHA2_CODES
                  (enables round-trip: canonicalize("SU") → "SU")
- shape="numeric": checks FORMER_NUMERIC_TO_ALPHA2 (for round-trip support)
"""

from __future__ import annotations

from paxman.capabilities.Country.notation import CountryNotation, normalize_name
from paxman.capabilities.Country.rules.data.iso_3166_ed2020_part3 import (
    FORMER_ALPHA2_CODES,
    FORMER_NAME_TO_ALPHA2,
    FORMER_NUMERIC_TO_ALPHA2,
)
from paxman.core.contract import Contract
from paxman.core.domain import Provenance, Rule, RuleStrategy


def _normalize_numeric_key(value: str) -> str:
    """Zero-pad numeric value to 3 digits (M49 standard format)."""
    try:
        return f"{int(value):03d}"
    except ValueError:
        return value


# Normalized former-name lookup view: keys normalized with the shared Country
# syntax normalizer so grammar tokens and rule lookups agree; values unchanged.
FORMER_NAME_TO_ALPHA2_NORMALIZED: dict[str, str] = {
    normalize_name(name): code for name, code in FORMER_NAME_TO_ALPHA2.items()
}

PUBLICATION = Provenance(
    authority="ISO",
    specification_name="ISO 3166-3",
    kind="specification",
    reference_url="https://www.iso.org/standard/72484.html",
    version="2020",
    lifecycle="active",
    publication_year=2020,
)


class SectionHistoricalNames(Rule[CountryNotation]):
    """ISO 3166-3 Section 4.2: formerly used country names.

    Validates that a notation represents a formerly used country name
    per ISO 3166-3. Returns the historical entity's own former alpha-2
    code as the canonical value.

    Activation is engine-owned: the engine runs this rule only when the
    contract enables ``include_historical``, via ``Rule.requires_features``.
    """

    name = "Section-historical-names"
    strategy = RuleStrategy.LOOKUP_TABLE
    provenance = PUBLICATION
    citation = "ISO 3166-3:2020 (formerly used names)"
    target_semantics = frozenset(
        {"name_recognition", "alpha2_recognition", "numeric_recognition"}
    )
    requires_features = frozenset({"include_historical"})

    def matches(self, notation: CountryNotation, contract: Contract) -> bool:
        """Check if notation is a valid formerly used country reference.

        Validates notation/table membership only. Whether the rule runs at
        all is decided by the engine from ``requires_features``.

        Accepts multiple shapes:
        - name:    checks FORMER_NAME_TO_ALPHA2_NORMALIZED
        - alpha2:  checks FORMER_ALPHA2_CODES (for round-trip support)
        - numeric: checks FORMER_NUMERIC_TO_ALPHA2 (for round-trip support)

        Args:
            notation: Country notation to validate.
            contract: Contract configuration.

        Returns:
            True if notation is a valid formerly used country.
        """
        if notation.shape == "name":
            return normalize_name(notation.value) in FORMER_NAME_TO_ALPHA2_NORMALIZED

        if notation.shape == "alpha2":
            return notation.value.upper() in FORMER_ALPHA2_CODES

        if notation.shape == "numeric":
            return _normalize_numeric_key(notation.value) in FORMER_NUMERIC_TO_ALPHA2

        return False

    def normalize(self, notation: CountryNotation, contract: Contract) -> str:
        """Normalize to the historical entity's own former alpha-2 code.

        Args:
            notation: Validated notation.
            contract: Contract configuration.

        Returns:
            Former alpha-2 code of the historical country.
        """
        if notation.shape == "name":
            return FORMER_NAME_TO_ALPHA2_NORMALIZED[normalize_name(notation.value)]

        if notation.shape == "alpha2":
            return notation.value.upper()

        if notation.shape == "numeric":
            return FORMER_NUMERIC_TO_ALPHA2[_normalize_numeric_key(notation.value)]

        # Should not reach here if matches() properly validated; be defensive.
        return notation.value.upper()
