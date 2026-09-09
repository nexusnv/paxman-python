"""IETF RFC 7946 — GeoJSON position (Section 3.1.1)."""

from __future__ import annotations

from typing import ClassVar

from paxman.capabilities.Coordinates.notation import CoordinatesNotation
from paxman.capabilities.Coordinates.rules import components_valid, normalize_compact
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
        if not components_valid(notation):
            return False
        try:
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
        except (AttributeError, TypeError):
            return False
        return True

    def normalize(self, notation: CoordinatesNotation, contract: Contract) -> str:
        return normalize_compact(notation)
