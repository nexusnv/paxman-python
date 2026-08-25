"""US federal date rule — validates and normalizes dates with two-digit year support.

This module historically cited "US Federal Government, Federal Rules 2023" via
the USGS Board on Geographic Names. That provenance was inaccurate: the BGN
does not define date formats. US ``MM/DD/YYYY`` ordering is a de facto national
convention codified in the U.S. Government Publishing Office Style Manual,
Chapter 9 (Dates), and in NARA/OMB guidance (MM/DD/YYYY). The provenance below
is corrected to the GPO Style Manual 2016 (31st Edition) for audit traceability.
File name is retained for compatibility; the ``PUBLICATION`` inside is authoritative.

The rule validates both slash grammars (``us_recognition`` and
``european_recognition``) because either recognition can be interpreted under
either spec — see D3/B3 in the audit (4-candidate ambiguous design). The grammar
produces identical ``N1,N2,N3`` values for the same span; the rule's
interpretation (``N1=month, N2=day``) determines the candidate value.
"""

from __future__ import annotations

from datetime import datetime

from paxman.capabilities.Date.notation import DateNotation
from paxman.core.contract import Contract
from paxman.core.domain import Provenance, Rule, RuleStrategy

PUBLICATION = Provenance(
    authority="U.S. Government Publishing Office",
    specification_name="Style Manual",
    kind="policy",
    reference_url="https://www.govinfo.gov/content/pkg/GPO-STYLEMANUAL-2016/pdf/GPO-STYLEMANUAL-2016.pdf",
    version="2016",
    lifecycle="active",
    publication_year=2016,
)


class Section1DateFormat(Rule[DateNotation]):
    """US GPO Style Manual, 31st Edition (2016) Chapter 9 — Dates — MM/DD/YYYY.

    Validates ``MM/DD/YYYY`` with two-digit year expansion. Also validates
    ``DD/MM/YYYY`` spans (via ``european_calendar_date`` semantics) under US
    month-first interpretation — hence the cross-grammar doubling noted in the
    audit's B3 (4 candidates for an ambiguous slash input is intentional).

    Notation mapping (US grammar):
        N1 = month, N2 = day, N3 = year

    Provenance: U.S. GPO Style Manual, Chapter 9 — Dates (MM/DD/YYYY).
    """

    name = "Section 1-date-format"
    strategy = RuleStrategy.PARSER
    provenance = PUBLICATION
    citation = "Chapter 9 (dates) — MM/DD/YYYY"
    target_semantics = frozenset({"us_calendar_date", "european_calendar_date"})
    requires_features = frozenset()

    def _interpret_two_digit_year(self, year_str: str, contract: Contract) -> int:
        """Interpret two-digit year using contract's base year.

        Defensive: the base year is read from the contract's
        ``two_digit_base_year`` attribute when present, falling back to 2000
        otherwise. An explicit zero is a configured value and is honored
        rather than treated as unset. This helper never raises for contracts
        that lack the Date-specific parameter.

        This helper is shared with ``Section4DateFormat`` — keep the two in sync.

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
        """Try to parse as US date with two-digit year support."""
        try:
            month = int(notation.N1)
            day = int(notation.N2)
            year = self._interpret_two_digit_year(notation.N3, contract)
            datetime(year, month, day)
            return True
        except ValueError:
            return False

    def normalize(self, notation: DateNotation, contract: Contract) -> str:
        """Normalize to the default canonical ISO 8601 format."""
        month = int(notation.N1)
        day = int(notation.N2)
        year = self._interpret_two_digit_year(notation.N3, contract)

        return f"{year:04d}-{month:02d}-{day:02d}"
