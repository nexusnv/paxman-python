"""ISO 6709:2022 — coordinate structure and Annex H string expression."""

from __future__ import annotations

from typing import ClassVar

from paxman.capabilities.Coordinates.notation import CoordinatesNotation
from paxman.capabilities.Coordinates.rules import components_valid, normalize_compact
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
        return components_valid(notation)

    def normalize(self, notation: CoordinatesNotation, contract: Contract) -> str:
        return normalize_compact(notation)


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
        return components_valid(notation)

    def normalize(self, notation: CoordinatesNotation, contract: Contract) -> str:
        return normalize_compact(notation)
