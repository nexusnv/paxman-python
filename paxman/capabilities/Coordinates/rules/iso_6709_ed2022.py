"""ISO 6709:2022 — coordinate structure and Annex H string expression."""

from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import ClassVar

from paxman.capabilities.Coordinates.notation import CoordinatesNotation
from paxman.capabilities.Coordinates.rules import component_in_range, fold_compact
from paxman.core.contract import Contract
from paxman.core.domain import Provenance, Rule, RuleStrategy

PUBLICATION = Provenance(
    authority="ISO",
    specification_name="ISO 6709",
    kind="specification",
    reference_url="https://www.iso.org/standard/75147.html",
    version="2022",
    lifecycle="active",
    publication_year=2022,
)


class Section6CoordinateStructure(Rule[CoordinatesNotation]):
    """ISO 6709:2022 Section 6 — coordinate structure.

    Validates per-coord_shape structure: decimal/DMS/DDM/ISO 6709.
    Enforces sign/hemisphere consistency, hemisphere axis agreement,
    DMS unit ranges (minutes < 60, seconds < 60), ISO integer digit
    widths (2/4/6 lat, 3/5/7 lon — the grammar records width and
    consistency facts in ``defects``), and the numeric ranges
    lat in [-90,90], lon in [-180,180].
    """

    name = "Section 6-coordinate-structure"
    strategy = RuleStrategy.PARSER
    provenance = PUBLICATION
    citation = "Section 6 (Coordinate structure)"
    target_semantics: ClassVar[frozenset[str]] = frozenset({"coordinates_recognition"})
    requires_features: ClassVar[frozenset[str]] = frozenset()

    def matches(self, notation: CoordinatesNotation, contract: Contract) -> bool:
        try:
            # Structural facts recorded at recognition: a defective input has
            # no valid reading under this publication's coordinate law.
            if notation.defects:
                return False
            if notation.coord_shape not in {"dd", "ddm", "dms", "iso6709"}:
                return False
        except (AttributeError, TypeError):
            return False
        try:
            lat_str = notation.latitude
            lon_str = notation.longitude
            # defensive: must be strings
            if not isinstance(lat_str, str) or not isinstance(lon_str, str):
                return False
            # altitude may be None or string; validate if present
            if notation.altitude is not None and not isinstance(notation.altitude, str):
                return False
            # quick Decimal parse check (also catches empty / non-numeric)
            Decimal(lat_str)
            Decimal(lon_str)
            if notation.altitude is not None:
                Decimal(notation.altitude)
        except (InvalidOperation, ValueError, AttributeError, TypeError):
            return False
        # Level 2: numeric range (RFC 5870 §3.3 / §9.1 share the envelope)
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


class SectionAnnexHStringExpression(Rule[CoordinatesNotation]):
    """ISO 6709:2022 Annex H — string expression of a point.

    Validates the ISO 6709 carrier: coord_shape == iso6709, trailing
    solidus present, CRS label (when present) in the WGS 84 family, and
    the numeric ranges. Carrier facts are recorded by the grammar in
    ``defects``; any defect means this publication does not validate
    the input as a coordinate.
    """

    name = "Section Annex-h-string-expression"
    strategy = RuleStrategy.PARSER
    provenance = PUBLICATION
    citation = "Annex H (String expression of a point)"
    target_semantics: ClassVar[frozenset[str]] = frozenset({"coordinates_recognition"})
    requires_features: ClassVar[frozenset[str]] = frozenset()

    def matches(self, notation: CoordinatesNotation, contract: Contract) -> bool:
        try:
            if notation.defects:
                return False
            if notation.coord_shape != "iso6709":
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
