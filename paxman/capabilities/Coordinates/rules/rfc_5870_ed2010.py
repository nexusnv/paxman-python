"""IETF RFC 5870 — geo URI validity (Section 3.3)."""

from __future__ import annotations

from typing import ClassVar

from paxman.capabilities.Coordinates.notation import CoordinatesNotation
from paxman.capabilities.Coordinates.rules import components_valid, normalize_compact
from paxman.core.contract import Contract
from paxman.core.domain import Provenance, Rule, RuleStrategy

PUBLICATION = Provenance(
    authority="IETF",
    specification_name="RFC 5870",
    kind="specification",
    reference_url="https://www.rfc-editor.org/rfc/rfc5870.txt",
    version="5870",
    lifecycle="active",
    publication_year=2010,
)


class Section33GeoUriValidity(Rule[CoordinatesNotation]):
    """RFC 5870 Section 3.3 — geo URI validity.

    Validates the geo-URI branch: coord_shape == geo_uri, lat in
    [-90,90], lon in [-180,180], altitude as supplied, and the CRS
    parameter absent or the WGS 84 family (a foreign CRS is recorded
    as a ``foreign_crs`` defect by the grammar — no silent datum
    transform, §5.4 of the research report). Any recorded defect means
    the URI is not a valid WGS 84 geo URI.
    """

    name = "Section 3.3-geo-uri-validity"
    strategy = RuleStrategy.PARSER
    provenance = PUBLICATION
    citation = "Section 3.3 (Geo URI validity)"
    target_semantics: ClassVar[frozenset[str]] = frozenset({"coordinates_recognition"})
    requires_features: ClassVar[frozenset[str]] = frozenset()

    def matches(self, notation: CoordinatesNotation, contract: Contract) -> bool:
        try:
            if notation.defects:
                return False
            if notation.coord_shape != "geo_uri":
                return False
        except (AttributeError, TypeError):
            return False
        return components_valid(notation)

    def normalize(self, notation: CoordinatesNotation, contract: Contract) -> str:
        return normalize_compact(notation)
