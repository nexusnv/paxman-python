"""IETF RFC 7946 — GeoJSON position (Section 3.1.1)."""

from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import ClassVar

from paxman.capabilities.Coordinates.notation import CoordinatesNotation
from paxman.capabilities.Coordinates.rules import component_in_range, fold_compact
from paxman.core.contract import Contract
from paxman.core.domain import Provenance, Rule, RuleStrategy

PUBLICATION = Provenance(
    authority="IETF",
    specification_name="RFC 7946",
    kind="specification",
    reference_url="https://www.rfc-editor.org/rfc/rfc7946.txt",
    version="7946",
    lifecycle="active",
    publication_year=2016,
)


class Section311Position(Rule[CoordinatesNotation]):
    """RFC 7946 Section 3.1.1 — position.

    Validates the GeoJSON branch: coord_shape == geojson, 2 or 3
    elements (altitude optional), lat in [-90,90], lon in [-180,180].
    The lon-first input order is inverted by the grammar; this rule
    enforces the publication's element-count and range law. Any defect
    recorded at recognition invalidates the position.
    """

    name = "Section 3.1.1-position"
    strategy = RuleStrategy.PARSER
    provenance = PUBLICATION
    citation = "Section 3.1.1 (Position)"
    target_semantics: ClassVar[frozenset[str]] = frozenset({"coordinates_recognition"})
    requires_features: ClassVar[frozenset[str]] = frozenset()

    def matches(self, notation: CoordinatesNotation, contract: Contract) -> bool:
        try:
            if notation.defects:
                return False
            if notation.coord_shape != "geojson":
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
                # GeoJSON allows at most 3 elements: lon, lat, alt
                # altitude present means 3 elements — valid; we already
                # enforce via shape, no extra length check needed beyond
                # ensuring altitude is a valid number.
                pass
            # Check element count: compact split by ", " should be 2 or 3
            parts = [p.strip() for p in notation.compact.split(",")]
            if len(parts) not in (2, 3):
                return False
            # altitude presence must match compact length
            has_alt = notation.altitude is not None
            if has_alt and len(parts) != 3:
                return False
            if not has_alt and len(parts) == 3:
                return False
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
