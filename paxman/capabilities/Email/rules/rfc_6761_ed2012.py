"""RFC 6761 localhost rule — localhost email validation.

Per RFC 6761 §6.3, "localhost" is a special-use domain name that
resolves to the loopback interface. Published Feb 2013 (datatracker
lists 2013; provenance keeps 2012 for year-filter stability — year 2012
already gates localhost). Reference URL is the stable datatracker HTML.
"""

from __future__ import annotations

from paxman.capabilities.Email.notation import EmailNotation
from paxman.core.contract import Contract
from paxman.core.domain import (
    Provenance,
    Rule,
    RuleStrategy,
)

PUBLICATION = Provenance(
    authority="IETF",
    specification_name="RFC 6761",
    kind="specification",
    reference_url="https://datatracker.ietf.org/doc/html/rfc6761",
    version="2012",
    lifecycle="active",
    publication_year=2012,
)


class Section63localhost(Rule[EmailNotation]):
    """RFC 6761 Section 6.3 — localhost.

    Validates email addresses with localhost as the domain.
    Per RFC 6761, "localhost" is a special-use domain name that
    resolves to the loopback interface.
    """

    name = "Section 6.3-localhost"
    strategy = RuleStrategy.REGEX
    provenance = PUBLICATION
    citation = "Section 6.3 (localhost)"
    target_semantics = frozenset({"localhost_recognition"})
    requires_features = frozenset()

    def matches(self, notation: EmailNotation, contract: Contract) -> bool:
        return notation.domain_part == "localhost"

    def normalize(self, notation: EmailNotation, contract: Contract) -> str:
        return f"{notation.local_part}@localhost"
