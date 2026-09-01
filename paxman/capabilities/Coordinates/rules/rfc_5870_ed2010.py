"""IETF RFC 5870 — geo URI validity (Section 3.3)."""

from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import ClassVar

from paxman.capabilities.Coordinates.notation import CoordinatesNotation
from paxman.capabilities.Coordinates.rules import component_in_range
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


def _fold_compact(compact: str) -> str:
    parts = [p.strip() for p in compact.split(",")]
    folded: list[str] = []
    for p in parts:
        try:
            d = Decimal(p)
        except (InvalidOperation, ValueError, AttributeError):
            folded.append(p)
            continue
        if d == 0:
            folded.append("0")
        else:
            nd = d.normalize()
            if nd == 0:
                folded.append("0")
            else:
                folded.append(format(nd, "f"))
    return ", ".join(folded)


class Section33GeoUriValidity(Rule[CoordinatesNotation]):
    """RFC 5870 Section 3.3 — geo URI validity.

    Validates the geo-URI branch: coord_shape == geo_uri, lat in
    [-90,90], lon in [-180,180], altitude as supplied. CRS handling
    (wgs84 or absent) is enforced at recognition — foreign CRS yields
    no match, so this rule only sees wgs84-equivalent URIs.
    """

    name = "Section 3.3-geo-uri-validity"
    strategy = RuleStrategy.PARSER
    provenance = PUBLICATION
    citation = "Section 3.3 (Geo URI validity)"
    target_semantics: ClassVar[frozenset[str]] = frozenset({"coordinates_recognition"})
    requires_features: ClassVar[frozenset[str]] = frozenset()

    def matches(self, notation: CoordinatesNotation, contract: Contract) -> bool:
        try:
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
            return _fold_compact(notation.compact)
        except Exception:
            try:
                return str(getattr(notation, "compact", ""))
            except Exception:
                return ""
