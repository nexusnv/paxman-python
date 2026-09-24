"""UTS #46 status validation rule — statuses, hyphens, and ACE round trip.

Owns every hyphen check (D13 ``CheckHyphens=true``): leading/trailing
hyphen (RFC 1035 §2.3.1; RFC 1123 §2.1 relaxes the first character for
digits only), ``--`` at the 3rd/4th position without an ``xn--`` prefix
(RFC 5890 §2.3.2.1; RFC 5891 §4.2.3.1), the STD3 underscore rejection,
and the ACE adjudication for labels that arrive still encoded
(malformed, ASCII-only, NFC-unstable, or map-unstable decodes — the
round trip plus U-label genuineness checks in ``ace_decode_ok``; RFC
3492; RFC 5891 §4) — plus the UTS #46 status check itself (allowed:
``valid`` and ``deviation``; STD3 rules ON, so ``disallowed_STD3_*``
rejects). Well-formed ACE arrives already decoded (map step), so every
check here sees the U-label form.
"""

from __future__ import annotations

from paxman.capabilities.Domain.idna_processing import (
    ace_decode_ok,
    finalize,
    status_of,
)
from paxman.capabilities.Domain.notation import DomainNotation
from paxman.core.contract import Contract
from paxman.core.domain import Provenance, Rule, RuleStrategy

_ALLOWED_STATUSES = frozenset({"valid", "deviation"})

PUBLICATION = Provenance(
    authority="Unicode",
    specification_name="UTS #46",
    kind="specification",
    reference_url="https://www.unicode.org/reports/tr46/",
    version="18.0.0",
    lifecycle="active",
    publication_year=2026,
)


def uts46_ok(notation: DomainNotation) -> bool:
    """UTS #46 validity: ACE round trip, statuses, and hyphen checks."""
    for label in notation.labels:
        if label.startswith("-") or label.endswith("-"):
            return False
        if label.startswith("xn--"):
            if not ace_decode_ok(label):
                return False
        elif len(label) >= 4 and label[2] == "-" and label[3] == "-":
            return False
        for char in label:
            if status_of(ord(char)) not in _ALLOWED_STATUSES:
                return False
    return True


class UnicodeUts46Statuses(Rule[DomainNotation]):
    """UTS #46 statuses with STD3 rules plus hyphen and ACE checks."""

    name = "UTS46-statuses"
    strategy = RuleStrategy.PARSER
    provenance = PUBLICATION
    citation = "UTS #46 processing with STD3 rules"
    target_semantics = frozenset({"ascii_hostname", "idn_hostname"})
    requires_features = frozenset()

    def matches(self, notation: DomainNotation, contract: Contract) -> bool:
        """Return True when every label passes ACE, statuses, hyphens."""
        return uts46_ok(notation)

    def normalize(self, notation: DomainNotation, contract: Contract) -> str:
        """Return the canonical A-label form shared by every rule."""
        return finalize(notation.labels)
