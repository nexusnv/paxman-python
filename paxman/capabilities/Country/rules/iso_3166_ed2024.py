"""ISO 3166-1:2020 validation rules (data snapshot 2024).

All four sections (alpha-2, alpha-3, numeric, name) share the same
publication and lookup tables. The authoritative edition is ISO 3166-1:2020
(second edition, 2020-08); the data tables are a 2024 snapshot of the
ISO 3166-1 Online Browsing Platform (OBP) registry. Rules are co-located
in a single file to reflect this shared provenance.

All sections normalize to the default canonical alpha-2 representation;
presentation in alpha-3, numeric, or name format is owned by
``CountryCapability.format_value()``.
"""

from __future__ import annotations

from paxman.capabilities.Country.notation import CountryNotation, normalize_name
from paxman.capabilities.Country.rules.cldr_localized_ed2025 import (
    LOCALIZED_TO_ALPHA2_NORMALIZED,
)
from paxman.capabilities.Country.rules.data.iso_3166_ed2024 import (
    ALPHA2_CODES,
    ALPHA3_TO_ALPHA2,
    NAME_TO_ALPHA2,
    NUMERIC_TO_ALPHA2,
    SYNONYM_TO_ALPHA2,
)
from paxman.core.contract import Contract
from paxman.core.domain import Provenance, Rule, RuleStrategy

# Normalized name lookup views: keys are normalized with the shared Country
# syntax normalizer so grammar tokens and rule lookups agree; values are
# unchanged. Normalized keys that collide across or within the two tables
# always map to the same alpha-2 code.
NAME_TO_ALPHA2_NORMALIZED: dict[str, str] = {
    normalize_name(name): alpha2 for name, alpha2 in NAME_TO_ALPHA2.items()
}
SYNONYM_TO_ALPHA2_NORMALIZED: dict[str, str] = {
    normalize_name(name): alpha2 for name, alpha2 in SYNONYM_TO_ALPHA2.items()
}

PUBLICATION = Provenance(
    authority="ISO",
    specification_name="ISO 3166-1:2020",
    kind="registry",
    reference_url="https://www.iso.org/guest/en/ISO3166-1/RegistrationTable/Active%20country%20list.html",
    version="2020",
    lifecycle="active",
    publication_year=2020,
)


class SectionAlpha2Codes(Rule[CountryNotation]):
    """ISO 3166-1 Section: alpha-2 codes.

    Validates alpha-2 shape against the official list of 249 assigned codes.
    """

    name = "Section-alpha2-codes"
    strategy = RuleStrategy.LOOKUP_TABLE
    provenance = PUBLICATION
    citation = "ISO 3166-1 alpha-2 codes"
    target_semantics = frozenset({"alpha2_recognition"})
    requires_features = frozenset()

    def matches(self, notation: CountryNotation, contract: Contract) -> bool:
        """Check if notation is a valid alpha-2 code.

        Args:
            notation: Country notation to validate.
            contract: Contract configuration.

        Returns:
            True if notation.shape == "alpha2" AND value is in ALPHA2_CODES.
        """
        if notation.shape != "alpha2":
            return False
        return notation.value.upper() in ALPHA2_CODES

    def normalize(self, notation: CountryNotation, contract: Contract) -> str:
        """Normalize to the canonical alpha-2 code.

        Args:
            notation: Validated notation.
            contract: Contract configuration.

        Returns:
            Uppercase alpha-2 code.
        """
        return notation.value.upper()


class SectionAlpha3Codes(Rule[CountryNotation]):
    """ISO 3166-1 Section: alpha-3 codes.

    Validates alpha-3 shape against the official list of 249 assigned codes.
    """

    name = "Section-alpha3-codes"
    strategy = RuleStrategy.LOOKUP_TABLE
    provenance = PUBLICATION
    citation = "ISO 3166-1 alpha-3 codes"
    target_semantics = frozenset({"alpha3_recognition"})
    requires_features = frozenset()

    def matches(self, notation: CountryNotation, contract: Contract) -> bool:
        """Check if notation is a valid alpha-3 code.

        Args:
            notation: Country notation to validate.
            contract: Contract configuration.

        Returns:
            True if notation.shape == "alpha3" AND value is in ALPHA3_TO_ALPHA2.
        """
        if notation.shape != "alpha3":
            return False
        return notation.value.upper() in ALPHA3_TO_ALPHA2

    def normalize(self, notation: CountryNotation, contract: Contract) -> str:
        """Normalize to the canonical alpha-2 code.

        Args:
            notation: Validated notation.
            contract: Contract configuration.

        Returns:
            Alpha-2 code for the validated alpha-3 input.
        """
        return ALPHA3_TO_ALPHA2[notation.value.upper()]


class SectionNumericCodes(Rule[CountryNotation]):
    """ISO 3166-1 Section: numeric (M49) codes.

    Validates numeric shape against the official list of 249 assigned codes.
    """

    name = "Section-numeric-codes"
    strategy = RuleStrategy.LOOKUP_TABLE
    provenance = PUBLICATION
    citation = "ISO 3166-1 numeric (M49) codes"
    target_semantics = frozenset({"numeric_recognition"})
    requires_features = frozenset()

    def _normalize_key(self, value: str) -> str:
        """Zero-pad numeric value to 3 digits (M49 standard format)."""
        try:
            return f"{int(value):03d}"
        except ValueError:
            return value

    def matches(self, notation: CountryNotation, contract: Contract) -> bool:
        """Check if notation is a valid numeric code.

        Args:
            notation: Country notation to validate.
            contract: Contract configuration.

        Returns:
            True if notation.shape == "numeric" AND value is in NUMERIC_TO_ALPHA2.
        """
        if notation.shape != "numeric":
            return False
        return self._normalize_key(notation.value) in NUMERIC_TO_ALPHA2

    def normalize(self, notation: CountryNotation, contract: Contract) -> str:
        """Normalize to the canonical alpha-2 code.

        Args:
            notation: Validated notation.
            contract: Contract configuration.

        Returns:
            Alpha-2 code for the validated numeric input.
        """
        return NUMERIC_TO_ALPHA2[self._normalize_key(notation.value)]


class SectionNames(Rule[CountryNotation]):
    """ISO 3166-1 Section: official English short names.

    Validates name shape against the official list of 249 assigned names
    and their common synonyms (e.g., USA → US, UK → GB).
    """

    name = "Section-names"
    strategy = RuleStrategy.LOOKUP_TABLE
    provenance = PUBLICATION
    citation = "ISO 3166-1 official English short names"
    target_semantics = frozenset({"name_recognition"})
    requires_features = frozenset()

    def matches(self, notation: CountryNotation, contract: Contract) -> bool:
        """Check if notation is a valid country name or synonym.

        Single-authority precedence (see LOCALIZED_TO_ALPHA2_NORMALIZED in
        the CLDR rule): when localized matching is enabled, names owned by
        the CLDR localized table (e.g. "MEXICO" from "México") are validated
        only by the CLDR rule; this ISO rule defers so a localized name
        cannot also yield an ISO-provenance candidate.

        Args:
            notation: Country notation to validate.
            contract: Contract configuration.

        Returns:
            True if notation.shape == "name" AND the normalized value is in
            the normalized NAME_TO_ALPHA2 or SYNONYM_TO_ALPHA2 views, and the
            name is not CLDR-owned while localized matching is enabled.
        """
        if notation.shape != "name":
            return False
        key = normalize_name(notation.value)
        if (
            key not in NAME_TO_ALPHA2_NORMALIZED
            and key not in SYNONYM_TO_ALPHA2_NORMALIZED
        ):
            return False
        return not (
            getattr(contract, "include_localized", False)
            and key in LOCALIZED_TO_ALPHA2_NORMALIZED
        )

    def normalize(self, notation: CountryNotation, contract: Contract) -> str:
        """Normalize to the canonical alpha-2 code.

        Checks the normalized NAME view first, then falls back to the
        normalized SYNONYM view.

        Args:
            notation: Validated notation.
            contract: Contract configuration.

        Returns:
            Alpha-2 code for the validated name input.
        """
        key = normalize_name(notation.value)
        if key in NAME_TO_ALPHA2_NORMALIZED:
            return NAME_TO_ALPHA2_NORMALIZED[key]
        return SYNONYM_TO_ALPHA2_NORMALIZED[key]
