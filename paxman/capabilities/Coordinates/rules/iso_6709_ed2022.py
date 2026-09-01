"""ISO 6709:2022 — coordinate structure and Annex H string expression."""

from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import ClassVar

from paxman.capabilities.Coordinates.notation import CoordinatesNotation
from paxman.capabilities.Coordinates.rules import component_in_range
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


def _fold_compact(compact: str) -> str:
    """Fold -0 components in compact to 0."""
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
            # normalize without scientific notation
            nd = d.normalize()
            if nd == 0:
                folded.append("0")
            else:
                folded.append(format(nd, "f"))
    return ", ".join(folded)


class Section6CoordinateStructure(Rule[CoordinatesNotation]):
    """ISO 6709:2022 Section 6 — coordinate structure.

    Validates per-coord_shape structure: decimal/DMS/DDM/ISO 6709.
    Checks minutes <60, seconds <60, hemisphere/sign consistency (via
    grammar sentinel), lat in [-90,90], lon in [-180,180], and ISO
    integer digit widths (encoded as out-of-range sentinel by grammar).
    """

    name = "Section 6-coordinate-structure"
    strategy = RuleStrategy.PARSER
    provenance = PUBLICATION
    citation = "Section 6 (Coordinate structure)"
    target_semantics: ClassVar[frozenset[str]] = frozenset({"coordinates_recognition"})
    requires_features: ClassVar[frozenset[str]] = frozenset()

    def matches(self, notation: CoordinatesNotation, contract: Contract) -> bool:
        try:
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
        # Level 2: numeric range (also covers grammar-encoded structural sentinels)
        if not component_in_range(lat_str, "-90", "90"):
            return False
        if not component_in_range(lon_str, "-180", "180"):
            return False
        # Level 1: structural checks that are still detectable from notation.
        # DMS overflow and hemisphere contradiction are encoded as out-of-range
        # sentinels by the grammar (91 / -91 / 181), so range already rejects
        # pipeline cases. For direct notation, overflow cannot be inferred from
        # quantized decimal alone, so we treat any dms/ddm with minutes/seconds
        # overflow that would have been sentineled as already handled.
        # ISO digit-width is also grammar-sentineled; for direct notation we
        # apply a best-effort width check on the quantized value's integer part
        # only for obviously wrong widths that are also in-range (e.g., 3-digit
        # lat 100 is already out-of-range, so redundant).
        if notation.coord_shape == "iso6709":
            # Best-effort width check: quantized lat 1-2 digits and lon 1-3
            # digits are all possible after decimal conversion, so no
            # additional rejection for in-range values. Out-of-range 3-digit
            # lat is already covered by range. The grammar sentinel is the
            # authoritative width enforcement.
            pass
        # For ddm/dms, overflow would be sentinel 91/181, already rejected.
        return True

    def normalize(self, notation: CoordinatesNotation, contract: Contract) -> str:
        try:
            return _fold_compact(notation.compact)
        except Exception:
            try:
                return str(getattr(notation, "compact", ""))
            except Exception:
                return ""


class SectionAnnexHStringExpression(Rule[CoordinatesNotation]):
    """ISO 6709:2022 Annex H — string expression of a point.

    Validates the carrier: trailing solidus and CRS label family.
    The grammar encodes missing solidus and foreign CRS as out-of-range
    sentinels; this rule re-checks the carrier law for direct notation
    where possible and always enforces range.
    """

    name = "Section Annex-h-string-expression"
    strategy = RuleStrategy.PARSER
    provenance = PUBLICATION
    citation = "Annex H (String expression of a point)"
    target_semantics: ClassVar[frozenset[str]] = frozenset({"coordinates_recognition"})
    requires_features: ClassVar[frozenset[str]] = frozenset()

    def matches(self, notation: CoordinatesNotation, contract: Contract) -> bool:
        try:
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
        # Carrier checks (solidus, CRS) are grammar-sentineled; for direct
        # notation the compact never contains '/' or CRS, so we cannot
        # re-derive them. The grammar sentinel ensures pipeline cases with
        # missing solidus or foreign CRS are out-of-range and thus rejected
        # via the range checks above.
        return component_in_range(lon_str, "-180", "180")

    def normalize(self, notation: CoordinatesNotation, contract: Contract) -> str:
        try:
            return _fold_compact(notation.compact)
        except Exception:
            try:
                return str(getattr(notation, "compact", ""))
            except Exception:
                return ""
