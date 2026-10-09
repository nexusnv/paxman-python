"""MPC numbering rule (publication: HowNamed)."""

from __future__ import annotations

import re

from paxman.capabilities.MinorPlanet.notation import MinorPlanetNotation
from paxman.core.contract import Contract
from paxman.core.domain import Provenance, Rule, RuleStrategy

PUBLICATION = Provenance(
    authority="Minor Planet Center",
    specification_name="Numbering/naming process",
    kind="specification",
    reference_url="https://minorplanetcenter.net/iau/info/HowNamed.html",
    version="living document (fetched 2026-10-07)",
    lifecycle="active",
    publication_year=2026,
)

_NUMBER_RE = re.compile(r"^\([1-9][0-9]{0,7}\)$", re.ASCII)


class Section5PermanentNumber(Rule[MinorPlanetNotation]):
    """HowNamed Section 5 — parenthesized permanent-number shape."""

    name = "Section 5-permanent-number"
    strategy = RuleStrategy.PARSER
    provenance = PUBLICATION
    citation = "Section Numbering (parenthesized positive integer, no leading zeros)"
    target_semantics = frozenset({"minor_planet_recognition"})
    requires_features = frozenset()

    def matches(self, notation: MinorPlanetNotation, contract: Contract) -> bool:
        """Return True for parenthesized positive integers on this lane."""
        try:
            if notation.form != "number":
                return False
            return _NUMBER_RE.match(notation.designation) is not None
        except (TypeError, AttributeError):
            return False

    def normalize(self, notation: MinorPlanetNotation, contract: Contract) -> str:
        """Return the canonical parenthesized number."""
        try:
            return notation.designation
        except (TypeError, AttributeError):
            return ""
