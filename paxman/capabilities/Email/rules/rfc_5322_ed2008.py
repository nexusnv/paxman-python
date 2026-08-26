"""RFC 5322 addr-spec rule — standard email validation.

Implements the common-case ``dot-atom`` subset of RFC 5322 §3.4.1
``addr-spec = local-part "@" domain``. The full ``atext`` includes
``!#$%&'*+-/=?^_`{|}~``; this rule conservatively allows
``[A-Za-z0-9._%+-]`` for the local part and labels
``alphanum *("-" alphanum)`` for the domain. RFC 5322 (2008) is updated
by RFC 6854 (2013) but §3.4.1 is unchanged. Validation enforces
``dot-atom-text = 1*atext *("." 1*atext)`` (no consecutive/trailing
dots) and per-label hyphen rules (no leading/trailing hyphen, no empty
labels), per RFC 1035/5321 domain-label discipline.
"""

from __future__ import annotations

import re

from paxman.capabilities.Email.notation import EmailNotation
from paxman.core.contract import Contract
from paxman.core.domain import (
    Provenance,
    Rule,
    RuleStrategy,
)

PUBLICATION = Provenance(
    authority="IETF",
    specification_name="RFC 5322",
    kind="specification",
    reference_url="https://datatracker.ietf.org/doc/html/rfc5322",
    version="2008",
    lifecycle="active",
    publication_year=2008,
)

_LOCAL_PATTERN = re.compile(
    r"^(?!.*\.\.)[A-Za-z0-9](?:[A-Za-z0-9._%+\-]*[A-Za-z0-9])?$"
)
_DOMAIN_PATTERN = re.compile(
    r"^(?!.*\.\.)(?:[A-Za-z0-9](?:[A-Za-z0-9\-]*[A-Za-z0-9])?\.)+[A-Za-z]{2,}$"
)


class Section341AddrSpec(Rule[EmailNotation]):
    """RFC 5322 Section 3.4.1 — addr-spec."""

    name = "Section 3.4.1-addr-spec"
    strategy = RuleStrategy.REGEX
    provenance = PUBLICATION
    citation = "Section 3.4.1 (addr-spec)"
    target_semantics = frozenset({"rfc5322_addr_spec"})
    requires_features = frozenset()

    def matches(self, notation: EmailNotation, contract: Contract) -> bool:
        return bool(
            _LOCAL_PATTERN.match(notation.local_part)
            and _DOMAIN_PATTERN.match(notation.domain_part)
        )

    def normalize(self, notation: EmailNotation, contract: Contract) -> str:
        return f"{notation.local_part}@{notation.domain_part.lower()}"
