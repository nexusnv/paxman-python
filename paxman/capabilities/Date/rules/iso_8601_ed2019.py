"""ISO 8601 date rule — validates and normalizes dates to ISO format.

Provenance: ISO 8601-1:2019 §5.2.1.1 calendar date (extended format YYYY-MM-DD).
This is the strict fixed-width path: 4-digit year (>=1000) and 2-digit
month/day are required at recognition time; single-digit ``2026-1-5`` is
``MISSING`` (not ``INVALID``). The slash-ISO grammar shares this rule's
semantics but is lenient (1-2 digit month/day) and zero-pads.
"""

from __future__ import annotations

from datetime import datetime

from paxman.capabilities.Date.notation import DateNotation
from paxman.core.contract import Contract
from paxman.core.domain import Provenance, Rule, RuleStrategy

PUBLICATION = Provenance(
    authority="ISO",
    specification_name="ISO 8601",
    kind="specification",
    reference_url="https://www.iso.org/standard/70907.html",
    version="2019",
    lifecycle="active",
    publication_year=2019,
)


class Section431CalendarDate(Rule[DateNotation]):
    """ISO 8601-1:2019 Section 5.2.1.1 — Calendar date (strict extended format).

    Validates both the dash-delimited ISO grammar (strict 2-digit month/day)
    and the slash-delimited lenient variant (which shares the same position
    mapping and canonical form). Year ``<1000`` is rejected here (enforcing
    the 4-digit extended format); slash US/European rules accept historic years
    including ``0026`` via four-digit ``0026`` or two-digit expansion (audit B2
    documents this asymmetry).

    Notation mapping (ISO 8601 grammar):
        N1 = year, N2 = month, N3 = day
    """

    name = "Section 5.2.1.1-calendar-date"
    strategy = RuleStrategy.PARSER
    provenance = PUBLICATION
    citation = "Section 5.2.1.1 (calendar date)"
    target_semantics = frozenset({"iso8601_calendar_date"})
    requires_features = frozenset()

    def matches(self, notation: DateNotation, contract: Contract) -> bool:
        """Try to parse as ISO 8601 date (strict year>=1000)."""
        try:
            year = int(notation.N1)
            if year < 1000:
                return False
            month = int(notation.N2)
            day = int(notation.N3)
            datetime(year, month, day)
            return True
        except ValueError:
            return False

    def normalize(self, notation: DateNotation, contract: Contract) -> str:
        """Normalize to ISO 8601 format (zero-padded)."""
        year = int(notation.N1)
        month = int(notation.N2)
        day = int(notation.N3)
        return f"{year:04d}-{month:02d}-{day:02d}"
