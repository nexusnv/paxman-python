"""MPC packed rules (publication: PackedDes)."""

from __future__ import annotations

from paxman.capabilities.MinorPlanet.notation import MinorPlanetNotation
from paxman.capabilities.MinorPlanet.rules.mpc_codec import mpc_unpack
from paxman.core.contract import Contract
from paxman.core.domain import Provenance, Rule, RuleStrategy

PUBLICATION = Provenance(
    authority="Minor Planet Center",
    specification_name="Packed provisional/permanent spec",
    kind="specification",
    reference_url="https://minorplanetcenter.net/iau/info/PackedDes.html",
    version="living document (fetched 2026-10-07)",
    lifecycle="active",
    publication_year=2026,
)


class Section3PackedProvisional(Rule[MinorPlanetNotation]):
    """PackedDes Section 3 — packed/extended/survey-packed decode coherence."""

    name = "Section 3-packed-provisional"
    strategy = RuleStrategy.PARSER
    provenance = PUBLICATION
    citation = "Sections Provisional Designations (packed 7-char, survey, tilde)"
    target_semantics = frozenset({"minor_planet_recognition"})
    requires_features = frozenset()

    def matches(self, notation: MinorPlanetNotation, contract: Contract) -> bool:
        """Return True when the packed spelling decodes coherently."""
        try:
            if notation.form not in ("packed", "extended", "survey_packed"):
                return False
            if not notation.packed:
                return False
            return mpc_unpack(notation.packed) is not None
        except (TypeError, AttributeError):
            return False

    def normalize(self, notation: MinorPlanetNotation, contract: Contract) -> str:
        """Return the canonical unpacked designation."""
        try:
            decoded = mpc_unpack(notation.packed)
            return decoded if decoded is not None else notation.designation
        except (TypeError, AttributeError):
            return notation.designation


class Section4PackedNumber(Rule[MinorPlanetNotation]):
    """PackedDes Section 4 — packed permanent-number decode coherence."""

    name = "Section 4-packed-number"
    strategy = RuleStrategy.PARSER
    provenance = PUBLICATION
    citation = "Section Permanent Designations (5-char, letter, tilde)"
    target_semantics = frozenset({"minor_planet_recognition"})
    requires_features = frozenset()

    def matches(self, notation: MinorPlanetNotation, contract: Contract) -> bool:
        """Return True when the packed number decodes coherently."""
        try:
            if notation.form != "packed_number":
                return False
            if not notation.packed:
                return False
            return mpc_unpack(notation.packed) is not None
        except (TypeError, AttributeError):
            return False

    def normalize(self, notation: MinorPlanetNotation, contract: Contract) -> str:
        """Return the canonical parenthesized number."""
        try:
            decoded = mpc_unpack(notation.packed)
            return decoded if decoded is not None else notation.designation
        except (TypeError, AttributeError):
            return notation.designation
