"""UNSPSC rule — scaffolded placeholder (publication: United Nations Development Programme).

TODO(scaffold): implement matches()/normalize() against your authority.
"""

from __future__ import annotations

from paxman.capabilities.UNSPSC.notation import UNSPSCNotation
from paxman.core.contract import Contract
from paxman.core.domain import Provenance, Rule, RuleStrategy

PUBLICATION = Provenance(
    authority="United Nations Development Programme",
    specification_name="UNSPSC Codeset Release",
    kind="specification",
    reference_url="https://www.undp.org/unspsc",
    version="v26.0801 (2023-08-14)",  # TODO(scaffold): set when --spec-version is provided
    lifecycle="active",
    publication_year=2023,
)


class UNSPSCRule(Rule[UNSPSCNotation]):
    """Placeholder validation rule for UNSPSC.

    TODO(scaffold): rename to the real Section {X.Y.Z}-{description}; implement
    matches()/normalize() against your authority.
    """

    name = "Section 1-overview"  # TODO(scaffold): Section {X.Y.Z}-{description}
    strategy = RuleStrategy.REGEX  # TODO(scaffold): match strategy to representation
    provenance = PUBLICATION
    citation = "Section TODO"  # TODO(scaffold): real citation
    target_semantics = frozenset({"unspsc_recognition"})
    requires_features = frozenset()

    def matches(self, notation: UNSPSCNotation, contract: Contract) -> bool:
        """TODO(scaffold): return True when notation is valid per authority."""
        return True

    def normalize(self, notation: UNSPSCNotation, contract: Contract) -> str:
        """TODO(scaffold): return the canonical form of notation.value."""
        return notation.value
