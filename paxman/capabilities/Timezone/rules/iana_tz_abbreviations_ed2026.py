"""IANA Time Zone Database abbreviation refusal (release 2026d).

Bare abbreviations are recognized but never resolved: short-caps
backward Links carved out of the name lexicon (identifier equivalence
is not lexical abbreviation equivalence) and ambiguous abbreviations
with no single zone both refuse. A refused mention yields no candidate,
so the engine reports INVALID downstream — never a silent pick.
"""

from __future__ import annotations

from typing import ClassVar

from paxman.capabilities.Timezone.notation import TimezoneNotation
from paxman.core.contract import Contract
from paxman.core.domain import Provenance, Rule, RuleStrategy

PUBLICATION = Provenance(
    authority="IANA",
    specification_name="Time Zone Database",
    kind="registry",
    reference_url="https://data.iana.org/time-zones/theory.html",
    version="2026d",
    lifecycle="active",
    publication_year=2026,
)


class SectionAbbreviationRefusal(Rule[TimezoneNotation]):
    """Bare timezone abbreviations refuse: carved Links and ambiguous alike.

    Membership in the carved set (``CARVED_LINKS``: est/mst/hst/cet) or the
    refusal set (``REFUSAL_SET``: ist/cst/pst) means the abbreviation rule
    returns False; the rule owns no resolution target, so normalize() only
    echoes the mention best-effort and is never a canonicalization path.
    """

    name = "Section abbreviation-refusal"
    strategy = RuleStrategy.LOOKUP_TABLE
    provenance = PUBLICATION
    citation = (
        "theory.html (abbreviation ambiguity: IST/CST/PST) + "
        "backward short-caps Links (carve set, vendored File-Date 2026d)"
    )
    target_semantics: ClassVar[frozenset[str]] = frozenset({"timezone_abbreviation"})
    requires_features: ClassVar[frozenset[str]] = frozenset()

    def matches(self, notation: TimezoneNotation, contract: Contract) -> bool:
        # Refusal table: carved and ambiguous abbreviations alike are
        # recognized but never validated. Always False; recognized without
        # a candidate the engine reports INVALID downstream.
        if notation.family != "abbreviation":
            return False
        compact = notation.compact
        if not isinstance(compact, str) or not compact:
            return False
        return False

    def normalize(self, notation: TimezoneNotation, contract: Contract) -> str:
        compact = notation.compact
        if not isinstance(compact, str):
            # defensive: never raise; unreachable after matches()
            return "" if compact is None else str(compact)
        return compact
