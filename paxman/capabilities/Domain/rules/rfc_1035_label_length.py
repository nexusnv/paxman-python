"""RFC 1035 label-length validation rule — domain name size constraints.

RFC 1035 §2.3.4: labels are limited to 63 octets, names to 255 octets on
the wire (253 characters in textual form without the trailing dot).
Lengths are measured post-encode: each label is ACE-encoded first, so a
Unicode label whose A-label form exceeds 63 octets fails even when its
U-label form is short.
"""

from __future__ import annotations

from paxman.capabilities.Domain.idna_processing import ace_encode, finalize
from paxman.capabilities.Domain.notation import DomainNotation
from paxman.core.contract import Contract
from paxman.core.domain import Provenance, Rule, RuleStrategy

MAX_LABEL_OCTETS = 63
MAX_NAME_CHARS = 253

PUBLICATION = Provenance(
    authority="IETF",
    specification_name="RFC 1035",
    kind="specification",
    reference_url="https://www.rfc-editor.org/rfc/rfc1035",
    version="1987",
    lifecycle="active",
    publication_year=1987,
)


def label_lengths_ok(notation: DomainNotation) -> bool:
    """RFC 1035 §2.3.4 check over ACE-encoded labels and the joined name."""
    encoded = [ace_encode(label) for label in notation.labels]
    return (
        all(len(label) <= MAX_LABEL_OCTETS for label in encoded)
        and len(".".join(encoded)) <= MAX_NAME_CHARS
    )


class Rfc1035LabelLength(Rule[DomainNotation]):
    """RFC 1035 Section 2.3.4 — label and name length limits."""

    name = "Section-2.3.4-label-length"
    strategy = RuleStrategy.PARSER
    provenance = PUBLICATION
    citation = "RFC 1035 §2.3.4 size constraints"
    target_semantics = frozenset({"ascii_hostname", "idn_hostname"})
    requires_features = frozenset()

    def matches(self, notation: DomainNotation, contract: Contract) -> bool:
        """Return True when every encoded label and the name fit."""
        return label_lengths_ok(notation)

    def normalize(self, notation: DomainNotation, contract: Contract) -> str:
        """Return the canonical A-label form shared by every rule."""
        return finalize(notation.labels)
