"""MacAddress rule — scaffolded placeholder (publication: IEEE).

TODO(scaffold): implement matches()/normalize() against your authority.
"""

from __future__ import annotations

from paxman.capabilities.MacAddress.notation import MacAddressNotation
from paxman.core.contract import Contract
from paxman.core.domain import Provenance, Rule, RuleStrategy

PUBLICATION = Provenance(
    authority="IEEE",
    specification_name="IEEE Std 802-2024",
    kind="specification",
    reference_url="https://standards.ieee.org/ieee/802/10894",
    version=None,  # TODO(scaffold): set when --spec-version is provided
    lifecycle="active",
    publication_year=2024,
)


class MacAddressRule(Rule[MacAddressNotation]):
    """Placeholder validation rule for MacAddress.

    TODO(scaffold): rename to the real Section {X.Y.Z}-{description}; implement
    matches()/normalize() against your authority.
    """

    name = "Section 1-overview"  # TODO(scaffold): Section {X.Y.Z}-{description}
    strategy = RuleStrategy.REGEX  # TODO(scaffold): match strategy to representation
    provenance = PUBLICATION
    citation = "Section TODO"  # TODO(scaffold): real citation
    target_semantics = frozenset({"mac_address_recognition"})
    requires_features = frozenset()

    def matches(self, notation: MacAddressNotation, contract: Contract) -> bool:
        """TODO(scaffold): return True when notation is valid per authority."""
        return True

    def normalize(self, notation: MacAddressNotation, contract: Contract) -> str:
        """TODO(scaffold): return the canonical form of notation.value."""
        return notation.value
