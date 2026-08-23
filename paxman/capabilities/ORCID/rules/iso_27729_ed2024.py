"""ORCID rule — scaffolded placeholder (publication: ISO).

TODO(scaffold): implement matches()/normalize() against your authority.
"""

from __future__ import annotations

from paxman.capabilities.ORCID.notation import ORCIDNotation
from paxman.core.contract import Contract
from paxman.core.domain import Provenance, Rule, RuleStrategy

PUBLICATION = Provenance(
    authority="ISO",
    specification_name="ISO 27729:2024",
    kind="specification",
    reference_url="https://www.iso.org/standard/87177.html",
    version="2024-11",  # TODO(scaffold): set when --spec-version is provided
    lifecycle="active",
    publication_year=2024,
)


class ORCIDRule(Rule[ORCIDNotation]):
    """Placeholder validation rule for ORCID.

    TODO(scaffold): rename to the real Section {X.Y.Z}-{description}; implement
    matches()/normalize() against your authority.
    """

    name = "Section 1-overview"  # TODO(scaffold): Section {X.Y.Z}-{description}
    strategy = RuleStrategy.REGEX  # TODO(scaffold): match strategy to representation
    provenance = PUBLICATION
    citation = "Section TODO"  # TODO(scaffold): real citation
    target_semantics = frozenset({"orcid_recognition"})
    requires_features = frozenset()

    def matches(self, notation: ORCIDNotation, contract: Contract) -> bool:
        """TODO(scaffold): return True when notation is valid per authority."""
        return True

    def normalize(self, notation: ORCIDNotation, contract: Contract) -> str:
        """TODO(scaffold): return the canonical form of notation.value."""
        return notation.value
