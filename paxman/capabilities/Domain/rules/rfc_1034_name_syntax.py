"""RFC 1034 name-syntax validation rule — placeholder (filled in Task 6).

TODO(task-6): rename to the real Section-3.1-name-syntax; implement
matches()/normalize() against RFC 1034 §3.1.
"""

from __future__ import annotations

from paxman.capabilities.Domain.notation import DomainNotation
from paxman.core.contract import Contract
from paxman.core.domain import Provenance, Rule, RuleStrategy

PUBLICATION = Provenance(
    authority="IETF",
    specification_name="RFC 1034",
    kind="specification",
    reference_url="https://www.rfc-editor.org/rfc/rfc1034",
    version=None,  # TODO(task-6): set the spec version pin
    lifecycle="active",
    publication_year=1987,
)


class Rfc1034NameSyntax(Rule[DomainNotation]):
    """Placeholder validation rule for Domain.

    TODO(task-6): rename to the real Section-3.1-name-syntax; implement
    matches()/normalize() against RFC 1034 §3.1.
    """

    name = "Section 1-overview"  # TODO(task-6): Section-3.1-name-syntax
    strategy = RuleStrategy.REGEX  # TODO(task-6): PARSER
    provenance = PUBLICATION
    citation = "Section TODO"  # TODO(task-6): real citation
    target_semantics = frozenset({"ascii_hostname"})
    requires_features = frozenset()

    def matches(self, notation: DomainNotation, contract: Contract) -> bool:
        """TODO(task-6): return True when notation is valid per authority."""
        return True

    def normalize(self, notation: DomainNotation, contract: Contract) -> str:
        """TODO(task-6): return the canonical form of the notation."""
        return notation.raw
