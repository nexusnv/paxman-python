"""UUID structure rule — IETF RFC 9562 §4 (PARSER, always-active).

Single publication, single class: the RFC defines layout only — no check
digit, no registry, no geography. Version/variant nibbles are informative
(generation rules constrain minting, §4 constrains storage); Nil/Max pass
by structure.
"""

from __future__ import annotations

from paxman.capabilities.UUID.notation import UUIDNotation
from paxman.core.contract import Contract
from paxman.core.domain import Provenance, Rule, RuleStrategy

PUBLICATION = Provenance(
    authority="IETF",
    specification_name="RFC 9562",
    kind="specification",
    reference_url="https://www.rfc-editor.org/rfc/rfc9562",
    version="May 2024",
    lifecycle="active",
    publication_year=2024,
)

_HEX = frozenset("0123456789abcdef")


class Section4UUIDFormat(Rule[UUIDNotation]):
    """RFC 9562 §4: 128-bit value as 32 lowercase hex chars."""

    name = "Section 4-uuid-format"
    strategy = RuleStrategy.PARSER
    provenance = PUBLICATION
    citation = "Section 4 (128-bit format; hex-and-dash ABNF)"
    target_semantics = frozenset({"uuid_recognition"})
    requires_features = frozenset()

    def matches(self, notation: UUIDNotation, contract: Contract) -> bool:
        """True when compact is exactly 32 ASCII lowercase hex chars."""
        compact = notation.compact
        return len(compact) == 32 and all(ch in _HEX for ch in compact)

    def normalize(self, notation: UUIDNotation, contract: Contract) -> str:
        """Return the lowercase hyphenated canonical form."""
        return notation.hyphenated
