"""IETF RFC 5870 — geo URI validity (Section 3.3)."""

from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import ClassVar

from paxman.capabilities.Coordinates.notation import CoordinatesNotation
from paxman.capabilities.Coordinates.rules import component_in_range, fold_compact
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
        try:
            lat_str = notation.latitude
            lon_str = notation.longitude
            if not isinstance(lat_str, str) or not isinstance(lon_str, str):
                return False
            Decimal(lat_str)
            Decimal(lon_str)
            if notation.altitude is not None:
                if not isinstance(notation.altitude, str):
                    return False
                Decimal(notation.altitude)
        except (InvalidOperation, ValueError, AttributeError, TypeError):
            return False
        if not component_in_range(lat_str, "-90", "90"):
            return False
        return component_in_range(lon_str, "-180", "180")

    def normalize(self, notation: CoordinatesNotation, contract: Contract) -> str:
        try:
            return fold_compact(notation.compact)
        except (InvalidOperation, ValueError, TypeError, AttributeError):
            pass
        try:
            # Last-resort best-effort return: rules never raise, even for
            # hostile objects whose ``__str__`` itself raises.
            return str(getattr(notation, "compact", ""))
        except Exception:  # never-raise contract, last resort
            return ""
