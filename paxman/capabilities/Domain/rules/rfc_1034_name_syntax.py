"""RFC 1034 name-syntax validation rule — domain name shape.

RFC 1034 §3.1: a domain name has at least two labels and no empty label.
Single-label scope ("localhost"/intranet) is deliberately deferred: it
arrives only as a requires_features-gated rule, never as a knob read here.
"""

from __future__ import annotations

from paxman.capabilities.Domain.idna_processing import finalize
from paxman.capabilities.Domain.notation import DomainNotation
from paxman.core.contract import Contract
from paxman.core.domain import Provenance, Rule, RuleStrategy

PUBLICATION = Provenance(
    authority="IETF",
    specification_name="RFC 1034",
    kind="specification",
    reference_url="https://www.rfc-editor.org/rfc/rfc1034",
    version="1987",
    lifecycle="active",
    publication_year=1987,
)


def name_syntax_ok(notation: DomainNotation) -> bool:
    """RFC 1034 §3.1 shape check: >= 2 labels and no empty label."""
    return len(notation.labels) >= 2 and all(label != "" for label in notation.labels)


class Rfc1034NameSyntax(Rule[DomainNotation]):
    """RFC 1034 Section 3.1 — name syntax (label count and emptiness)."""

    name = "Section-3.1-name-syntax"
    strategy = RuleStrategy.PARSER
    provenance = PUBLICATION
    citation = "RFC 1034 §3.1 name syntax"
    target_semantics = frozenset({"ascii_hostname", "idn_hostname"})
    requires_features = frozenset()

    def matches(self, notation: DomainNotation, contract: Contract) -> bool:
        """Return True when the notation has >= 2 non-empty labels."""
        return name_syntax_ok(notation)

    def normalize(self, notation: DomainNotation, contract: Contract) -> str:
        """Return the canonical A-label form shared by every rule."""
        return finalize(notation.labels)
