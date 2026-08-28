"""Country capability — wires grammars and rules together."""

from __future__ import annotations

from collections.abc import Sequence

from paxman.capabilities.Country.contract import CountryContract
from paxman.capabilities.Country.grammar.alpha2_recognition import Alpha2Grammar
from paxman.capabilities.Country.grammar.alpha3_recognition import Alpha3Grammar
from paxman.capabilities.Country.grammar.name_recognition import NameGrammar
from paxman.capabilities.Country.grammar.numeric_recognition import NumericGrammar
from paxman.capabilities.Country.notation import CountryNotation, normalize_name
from paxman.capabilities.Country.rules.cldr_localized_ed2025 import (
    SectionLocalizedNames,
)
from paxman.capabilities.Country.rules.data.iso_3166_ed2024 import (
    ALPHA2_TO_ALPHA3,
    ALPHA2_TO_NAME,
    ALPHA2_TO_NUMERIC,
)
from paxman.capabilities.Country.rules.iso_3166_ed2024 import (
    SectionAlpha2Codes,
    SectionAlpha3Codes,
    SectionNames,
    SectionNumericCodes,
)
from paxman.capabilities.Country.rules.iso_3166_historical_ed2020 import (
    FORMER_NAME_TO_ALPHA2_NORMALIZED,
    SectionHistoricalNames,
)
from paxman.core.capability import Capability
from paxman.core.domain import Grammar, Rule

__all__ = ["CountryCapability", "CountryContract", "CountryNotation"]


class CountryCapability(Capability[CountryNotation]):
    """Country canonicalization capability.

    Canonicalizes country representations (alpha2, alpha3, numeric, name)
    to ISO 3166-1 alpha-2 codes with full provenance.
    """

    name = "country"

    def get_grammars(self) -> list[Grammar[CountryNotation]]:
        """Return all grammar instances.

        Returns:
            List of 4 grammars: alpha2, alpha3, numeric, name.
        """
        return [
            Alpha2Grammar(),
            Alpha3Grammar(),
            NumericGrammar(),
            NameGrammar(),
        ]

    def get_rules(self) -> list[Rule[CountryNotation]]:
        """Return all validation rule instances.

        Returns:
            List of 6 rules: alpha2, alpha3, numeric, name,
            cldr_localized, paxman_historical.
        """
        return [
            SectionAlpha2Codes(),
            SectionAlpha3Codes(),
            SectionNumericCodes(),
            SectionNames(),
            SectionLocalizedNames(),
            SectionHistoricalNames(),
        ]

    @staticmethod
    def create_contract(
        *,
        excluded_rules: Sequence[str] | None = None,
        pinned_rules: Sequence[str] | None = None,
        year: int | None = None,
        output_format: str | None = None,
        extra_grammars: Sequence[str] | None = None,
        suppress_common_words: bool = False,
        include_localized: bool = False,
        include_historical: bool = False,
    ) -> CountryContract:
        """Factory method for creating contracts with proper defaults.

        Args:
            excluded_rules: Rule names to exclude.
            pinned_rules: Pin to specific rules (takes precedence over excluded_rules).
            year: Year for temporal filtering.
            output_format: Output format for canonical values. Optional; one of
                "alpha2" (default), "alpha3", "numeric", "name".
            extra_grammars: Community grammar names (opt-in) to run alongside
                the shipped grammars, in order.
            include_localized: Enable CLDR multilingual names.
            include_historical: Enable deprecated country names.

        Returns:
            Configured CountryContract instance.
        """
        return CountryContract(
            excluded_rules=tuple(excluded_rules) if excluded_rules else (),
            pinned_rules=tuple(pinned_rules) if pinned_rules is not None else None,
            year=year,
            output_format=output_format,
            extra_grammars=tuple(extra_grammars) if extra_grammars else (),
            suppress_common_words=suppress_common_words,
            include_localized=include_localized,
            include_historical=include_historical,
        )

    def format_value(
        self,
        value: str,
        output_format: str | None,
        notation: CountryNotation,
    ) -> str:
        """Render a default alpha-2 canonical value in the requested format.

        The default ``"alpha2"`` path is the identity: the rule-produced
        alpha-2 canonical value is returned unchanged. ``"alpha3"``,
        ``"numeric"``, and ``"name"`` requests map the current alpha-2 code
        through the ISO 3166-1 conversion tables. Former codes that are
        absent from the current tables (e.g. ``"SU"`` for the USSR) pass
        through unchanged because there is no current mapping to convert to.

        Args:
            value: The default canonical value produced by ``Rule.normalize()``
                (an ISO 3166-1 alpha-2 code).
            output_format: The contract's resolved output format (``"alpha2"``,
                ``"alpha3"``, ``"numeric"``, or ``"name"``).
            notation: The original country notation that produced the canonical
                value, retained for interface compatibility.

        Returns:
            The value rendered in the requested format.
        """
        if notation.shape == "name":
            historical_value = FORMER_NAME_TO_ALPHA2_NORMALIZED.get(
                normalize_name(notation.value)
            )
            if historical_value == value:
                return value
        if output_format == "alpha3":
            return ALPHA2_TO_ALPHA3.get(value, value)
        if output_format == "numeric":
            return ALPHA2_TO_NUMERIC.get(value, value)
        if output_format == "name":
            return ALPHA2_TO_NAME.get(value, value)
        return value
