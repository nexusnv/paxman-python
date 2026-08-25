"""EN 50160 date rule — validates and normalizes European DD/MM/YYYY dates.

This module historically cited "CENELEC EN 50160:2010 Voltage characteristics of
electricity". That provenance was inaccurate: EN 50160 is a power-quality
standard and does not define calendar date formats. European ``DD/MM/YYYY``
ordering is a civilian locale convention documented in Unicode CLDR (locale
data for en-GB/fr/de etc.) and in national practice (BS 3733, DIN 1355).
The provenance below is corrected to Unicode CLDR (aligns with Country/Currency
capabilities). File name is retained for compatibility; the ``PUBLICATION``
inside is authoritative.

The rule validates both slash grammars for the same cross-validation reason
as the US rule (see its docstring and audit B3).
"""

from __future__ import annotations

from datetime import datetime

from paxman.capabilities.Date.notation import DateNotation
from paxman.core.contract import Contract
from paxman.core.domain import Provenance, Rule, RuleStrategy

PUBLICATION = Provenance(
    authority="Unicode CLDR",
    specification_name="Unicode CLDR",
    kind="specification",
    reference_url="https://cldr.unicode.org/",
    version="47",
    lifecycle="active",
    publication_year=2025,
)


class Section4DateFormat(Rule[DateNotation]):
    """Unicode CLDR — European date format DD/MM/YYYY.

    Validates ``DD/MM/YYYY`` with two-digit year expansion. Also validates
    ``MM/DD/YYYY`` spans (via ``us_calendar_date`` semantics) under European
    day-first interpretation.

    Notation mapping (European grammar):
        N1 = day, N2 = month, N3 = year

    Provenance: Unicode CLDR date patterns (European DD/MM/YYYY ordering).
    """

    name = "Section 4-date-format"
    strategy = RuleStrategy.PARSER
    provenance = PUBLICATION
    citation = "Date and time patterns — DD/MM/YYYY"
    target_semantics = frozenset({"us_calendar_date", "european_calendar_date"})
    requires_features = frozenset()

    def _interpret_two_digit_year(self, year_str: str, contract: Contract) -> int:
        """Interpret two-digit year using contract's base year.

        Defensive: the base year is read from the contract's
        ``two_digit_base_year`` attribute when present, falling back to 2000
        otherwise. An explicit zero is a configured value and is honored
        rather than treated as unset. This helper never raises for contracts
        that lack the Date-specific parameter.

        This helper is shared with ``Section1DateFormat`` — keep the two in sync.

        Args:
            year_str: The year field from the notation.
            contract: Contract configuration.

        Returns:
            The full year (base year + two-digit offset, or the year as-is).
        """
        if len(year_str) == 2:
            base_year = getattr(contract, "two_digit_base_year", None)
            if base_year is None:
                base_year = 2000
            return base_year + int(year_str)
        return int(year_str)

    def matches(self, notation: DateNotation, contract: Contract) -> bool:
        """Try to parse as European date DD/MM/YYYY."""
        try:
            day = int(notation.N1)
            month = int(notation.N2)
            year = self._interpret_two_digit_year(notation.N3, contract)
            datetime(year, month, day)
            return True
        except ValueError:
            return False

    def normalize(self, notation: DateNotation, contract: Contract) -> str:
        """Normalize to the default canonical ISO 8601 format."""
        day = int(notation.N1)
        month = int(notation.N2)
        year = self._interpret_two_digit_year(notation.N3, contract)

        return f"{year:04d}-{month:02d}-{day:02d}"
