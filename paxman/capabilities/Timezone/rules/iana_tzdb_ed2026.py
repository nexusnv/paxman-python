"""IANA Time Zone Database identifier validation (release 2026d).

Zone-key membership plus backward Link resolution over the vendored
snapshot tables, with POSIX SystemV Zones behind the ``include_systemv``
contract flag. Folded mentions restore canonical case through the
lowered lookup views (the tzdb POSIX component rules forbid
case-variant collisions, so folding is injective by construction).
"""

from __future__ import annotations

from typing import ClassVar

from paxman.capabilities.Timezone.notation import TimezoneNotation
from paxman.capabilities.Timezone.rules.data.abbreviation_map import CARVED_LINKS
from paxman.capabilities.Timezone.rules.data.iana_zone_identifiers import (
    IANA_ZONE_IDENTIFIERS,
)
from paxman.capabilities.Timezone.rules.data.iana_zone_links import IANA_ZONE_LINKS
from paxman.core.contract import Contract
from paxman.core.domain import Provenance, Rule, RuleStrategy

PUBLICATION = Provenance(
    authority="IANA",
    specification_name="Time Zone Database",
    kind="registry",
    reference_url="https://www.iana.org/time-zones",
    version="2026d",
    lifecycle="active",
    publication_year=2026,
)

# Lowered views: the name grammar folds before lookup; the rule restores
# canonical case from these maps (BIC fold precedent).
_FOLDED_TO_CANONICAL: dict[str, str] = {
    key.lower(): key for key in IANA_ZONE_IDENTIFIERS
}
_FOLDED_LINKS: dict[str, str] = {
    source.lower(): target for source, target in IANA_ZONE_LINKS.items()
}

# POSIX SystemV Zones declared in backward (EST5EDT/CST6CDT/MST7MDT/PST8PDT).
# They are Zones, not Links: canonical form is themselves, uppercase as
# authored. Owned exclusively by SectionSystemVZones below; the always-active
# sections exclude them so the default contract stays INVALID for these keys.
_SYSTEMV_ZONES: dict[str, str] = {
    "est5edt": "EST5EDT",
    "cst6cdt": "CST6CDT",
    "mst7mdt": "MST7MDT",
    "pst8pdt": "PST8PDT",
}


class SectionZoneKeyMembership(Rule[TimezoneNotation]):
    """IANA identifier membership, case-exact after the grammar fold."""

    name = "Section zone-key-membership"
    strategy = RuleStrategy.LOOKUP_TABLE
    provenance = PUBLICATION
    citation = "zone1970.tab col 3 + backward Links + etcetera (vendored File-Date)"
    target_semantics: ClassVar[frozenset[str]] = frozenset({"timezone_name"})
    requires_features: ClassVar[frozenset[str]] = frozenset()

    def matches(self, notation: TimezoneNotation, contract: Contract) -> bool:
        """Check whether the notation is a known IANA zone identifier."""
        if notation.family != "name":
            return False
        compact = notation.compact
        if not isinstance(compact, str) or not compact:
            return False
        folded = compact.lower()
        if folded in _SYSTEMV_ZONES:
            return False
        return folded in _FOLDED_TO_CANONICAL

    def normalize(self, notation: TimezoneNotation, contract: Contract) -> str:
        """Return the canonical-case zone identifier."""
        compact = notation.compact
        if not isinstance(compact, str):
            # defensive: never raise; unreachable after matches()
            return "" if compact is None else str(compact)
        return _FOLDED_TO_CANONICAL.get(compact.lower(), compact)


class SectionLinkResolution(Rule[TimezoneNotation]):
    """IANA Link equivalence: registry-declared aliases resolve to canonical."""

    name = "Section link-resolution"
    strategy = RuleStrategy.LOOKUP_TABLE
    provenance = PUBLICATION
    citation = "backward Link TARGET LINK-NAME lines (vendored File-Date 2026d)"
    target_semantics: ClassVar[frozenset[str]] = frozenset({"timezone_name"})
    requires_features: ClassVar[frozenset[str]] = frozenset()

    def matches(self, notation: TimezoneNotation, contract: Contract) -> bool:
        """Check whether the notation is a known IANA Link alias."""
        if notation.family != "name":
            return False
        compact = notation.compact
        if not isinstance(compact, str) or not compact:
            return False
        folded = compact.lower()
        if folded in _SYSTEMV_ZONES:
            return False
        if folded in CARVED_LINKS:
            # Short-caps backward Links are carved into the abbreviation
            # family: the name rule never resolves them.
            return False
        return folded in _FOLDED_LINKS

    def normalize(self, notation: TimezoneNotation, contract: Contract) -> str:
        """Resolve the Link alias to its canonical zone identifier."""
        compact = notation.compact
        if not isinstance(compact, str):
            # defensive: never raise; unreachable after matches()
            return "" if compact is None else str(compact)
        return _FOLDED_LINKS.get(compact.lower(), compact)


class SectionSystemVZones(Rule[TimezoneNotation]):
    """IANA backward SystemV Zones, gated on the ``include_systemv`` flag.

    Activation is engine-owned: the engine drops this rule unless the
    contract enables ``include_systemv`` (a dropped rule yields INVALID
    downstream); matches() itself validates membership only.
    """

    name = "Section systemv-zones"
    strategy = RuleStrategy.LOOKUP_TABLE
    provenance = PUBLICATION
    citation = (
        "backward SystemV Zones EST5EDT/CST6CDT/MST7MDT/PST8PDT "
        "(vendored File-Date 2026d)"
    )
    target_semantics: ClassVar[frozenset[str]] = frozenset({"timezone_name"})
    requires_features: ClassVar[frozenset[str]] = frozenset({"include_systemv"})

    def matches(self, notation: TimezoneNotation, contract: Contract) -> bool:
        """Check whether the notation is a SystemV zone key."""
        if notation.family != "name":
            return False
        compact = notation.compact
        if not isinstance(compact, str) or not compact:
            return False
        return compact.lower() in _SYSTEMV_ZONES

    def normalize(self, notation: TimezoneNotation, contract: Contract) -> str:
        """Return the canonical uppercase SystemV zone."""
        compact = notation.compact
        if not isinstance(compact, str):
            # defensive: never raise; unreachable after matches()
            return "" if compact is None else str(compact)
        return _SYSTEMV_ZONES.get(compact.lower(), compact)
