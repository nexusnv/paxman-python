"""UNDP UNSPSC codeset rule: stem membership plus ancestor liveness.

The stem must exist in the pinned snapshot AND every pair-prefix
ancestor (``SS000000``, ``SSFF0000``, ``SSFFCC00``) must resolve against
the live rows plus the flagged synthesized ancestors. Hierarchy truth
lives in the snapshot, not the type: ``43001503``-style mid-zero
anomalies fail here even when padding-consistent, and a synthesized
ancestor alone (e.g. ``57110000``) is INVALID — synthesis serves the
ancestor walk only, never stem membership.
"""

from __future__ import annotations

from paxman.capabilities.UNSPSC.notation import UNSPSCNotation
from paxman.capabilities.UNSPSC.rules.data.unspsc_codeset import (
    CODESET_VERSION,
    LIVE_STEMS,
    SYNTHESIZED_ANCESTORS,
)
from paxman.core.contract import Contract
from paxman.core.domain import Provenance, Rule, RuleStrategy

PUBLICATION = Provenance(
    authority="United Nations Development Programme",
    specification_name="UNSPSC Codeset (UNGM live export)",
    kind="registry",
    reference_url="https://www.ungm.org/Public/UNSPSC",
    version=CODESET_VERSION,
    lifecycle="active",
    publication_year=2026,
)


def _ancestors(stem: str) -> tuple[str, str, str]:
    """Pair-prefix ancestors: segment, family, class rows."""
    return (stem[:2] + "000000", stem[:4] + "0000", stem[:6] + "00")


def _is_member(notation: UNSPSCNotation) -> bool:
    """Stem is a live row and all pair-prefix ancestors resolve.

    Synthesized ancestors serve the ancestor walk ONLY: a synthesized
    code alone is not a live row and resolves INVALID.
    """
    stem = notation.digits
    if len(stem) != 8 or not stem.isascii() or not stem.isdigit():
        return False
    if stem not in LIVE_STEMS:
        return False
    live = LIVE_STEMS | SYNTHESIZED_ANCESTORS
    return all(ancestor in live for ancestor in _ancestors(stem))


class Section3CodesetMembership(Rule[UNSPSCNotation]):
    """UNDP codeset Section 3 — stem membership with live ancestors."""

    name = "Section 3-codeset-membership"
    strategy = RuleStrategy.LOOKUP_TABLE
    provenance = PUBLICATION
    citation = "Codeset membership (stem + SS000000/SSFF0000/SSFFCC00 live)"
    target_semantics = frozenset({"unspsc_recognition"})
    requires_features = frozenset()

    def matches(self, notation: UNSPSCNotation, contract: Contract) -> bool:
        """Check whether the stem and its ancestors are live rows."""
        return _is_member(notation)

    def normalize(self, notation: UNSPSCNotation, contract: Contract) -> str:
        """Normalize to the 8-digit compact stem."""
        return notation.digits
