"""MPC unpacked + survey rules (publication: DesDoc)."""

from __future__ import annotations

import re

from paxman.capabilities.MinorPlanet.notation import MinorPlanetNotation
from paxman.core.contract import Contract
from paxman.core.domain import Provenance, Rule, RuleStrategy

PUBLICATION = Provenance(
    authority="Minor Planet Center",
    specification_name="Unpacked provisional designation definition",
    kind="specification",
    reference_url="https://minorplanetcenter.net/iau/info/DesDoc.html",
    version="living document (fetched 2026-10-07)",
    lifecycle="active",
    publication_year=2026,
)

_YEAR = r"(?:A[89]\d{2}|19\d{2}|20\d{2})"
_UNPACKED_RE = re.compile(rf"^(?:{_YEAR}) [A-HJ-Y][A-HJ-Z](?:[1-9]\d*)?$", re.ASCII)
_APREFIX_RE = re.compile(rf"^A/(?:{_YEAR}) [A-HJ-Y][A-HJ-Z]?(?:[1-9]\d*)?$", re.ASCII)
_SURVEY_RE = re.compile(r"^[1-9]\d{0,3} (?:P-L|T-[123])$", re.ASCII)


class Section1UnpackedProvisionalStructure(Rule[MinorPlanetNotation]):
    """DesDoc Section 1 — unpacked provisional structure."""

    name = "Section 1-unpacked-provisional-structure"
    strategy = RuleStrategy.PARSER
    provenance = PUBLICATION
    citation = "Sections New-Style Provisional Designations (year/order/cycle)"
    target_semantics = frozenset({"minor_planet_recognition"})
    requires_features = frozenset()

    def matches(self, notation: MinorPlanetNotation, contract: Contract) -> bool:
        """Return True for coherent unpacked provisionals on this lane."""
        try:
            if notation.form != "provisional":
                return False
            designation = notation.designation
            if not isinstance(designation, str):
                return False
            if designation.startswith("A/"):
                return _APREFIX_RE.match(designation) is not None
            return _UNPACKED_RE.match(designation) is not None
        except (TypeError, AttributeError):
            return False

    def normalize(self, notation: MinorPlanetNotation, contract: Contract) -> str:
        """Return the canonical unpacked designation."""
        try:
            return notation.designation
        except (TypeError, AttributeError):
            return ""


class Section2SurveyDesignation(Rule[MinorPlanetNotation]):
    """DesDoc Section 2 — Palomar-Leiden / Trojan survey designations."""

    name = "Section 2-survey-designation"
    strategy = RuleStrategy.PARSER
    provenance = PUBLICATION
    citation = "Section Survey Designations (number + P-L/T-1/T-2/T-3)"
    target_semantics = frozenset({"minor_planet_recognition"})
    requires_features = frozenset()

    def matches(self, notation: MinorPlanetNotation, contract: Contract) -> bool:
        """Return True for survey designations on this lane."""
        try:
            if notation.form != "survey":
                return False
            return _SURVEY_RE.match(notation.designation) is not None
        except (TypeError, AttributeError):
            return False

    def normalize(self, notation: MinorPlanetNotation, contract: Contract) -> str:
        """Return the canonical survey designation."""
        try:
            return notation.designation
        except (TypeError, AttributeError):
            return ""
