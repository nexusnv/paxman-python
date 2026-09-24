"""RFC 1034 name-syntax validation rule — domain name shape.

RFC 1034 §3.1 reserves the null label for the root (no empty labels);
the ≥2-label minimum is Domain scope policy, not RFC text (§3.5 permits
single-label domains) — single-label scope ("localhost"/intranet) is
deliberately deferred and arrives only as a requires_features-gated rule.
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
    """Shape check: no empty label (RFC 1034 §3.1) and ≥2 labels (policy)."""
    return len(notation.labels) >= 2 and all(label != "" for label in notation.labels)


class Rfc1034NameSyntax(Rule[DomainNotation]):
    """RFC 1034 Section 3.1 no-empty-label plus the Domain two-label minimum."""

    name = "Section-3.1-name-syntax"
    strategy = RuleStrategy.PARSER
    provenance = PUBLICATION
    citation = "RFC 1034 §3.1 name syntax; ≥2-label minimum is Domain policy"
    target_semantics = frozenset({"ascii_hostname", "idn_hostname"})
    requires_features = frozenset()

    def matches(self, notation: DomainNotation, contract: Contract) -> bool:
        """Return True when the notation has >= 2 non-empty labels."""
        return name_syntax_ok(notation)

    def normalize(self, notation: DomainNotation, contract: Contract) -> str:
        """Return the canonical A-label form shared by every rule."""
        return finalize(notation.labels)
