"""IANA root-zone membership rule — the ADR-0012 LOOKUP chokepoint.

The only ``RuleStrategy.LOOKUP_TABLE`` rule in the capability. It ANDs the
four public rule predicates with encoded-TLD membership in the IANA
tlds-alpha snapshot: when it fails there is no LOOKUP corroboration on
the recognition, so the orchestrator drops every PARSER candidate and
the qualified set is empty (INVALID with recognitions, never an
uncorroborated SUCCESS). Intra-capability predicate imports only —
import-linter bans cross-capability imports, not these.
"""

from __future__ import annotations

from paxman.capabilities.Domain.idna_processing import ace_encode, finalize
from paxman.capabilities.Domain.notation import DomainNotation
from paxman.capabilities.Domain.rules.data.root_zone_tlds import ROOT_ZONE_TLDS
from paxman.capabilities.Domain.rules.rfc_1034_name_syntax import name_syntax_ok
from paxman.capabilities.Domain.rules.rfc_1035_label_length import (
    label_lengths_ok,
)
from paxman.capabilities.Domain.rules.rfc_5893_bidi_context import bidi_ok
from paxman.capabilities.Domain.rules.unicode_uts46_statuses import uts46_ok
from paxman.core.contract import Contract
from paxman.core.domain import Provenance, Rule, RuleStrategy

PUBLICATION = Provenance(
    authority="IANA",
    specification_name="tlds-alpha-by-domain.txt",
    kind="registry",
    reference_url="https://data.iana.org/TLD/tlds-alpha-by-domain.txt",
    version="IANA tlds-alpha v2026092300",
    lifecycle="active",
    publication_year=2026,
)


class IanaRootZoneMembership(Rule[DomainNotation]):
    """IANA Root Zone Database membership over the encoded TLD."""

    name = "root-zone-membership"
    strategy = RuleStrategy.LOOKUP_TABLE
    provenance = PUBLICATION
    citation = "IANA Root Zone Database membership"
    target_semantics = frozenset({"ascii_hostname", "idn_hostname"})
    requires_features = frozenset()

    def matches(self, notation: DomainNotation, contract: Contract) -> bool:
        """Return True when every predicate holds and the TLD is delegated."""
        return (
            name_syntax_ok(notation)
            and label_lengths_ok(notation)
            and uts46_ok(notation)
            and bidi_ok(notation)
            and ace_encode(notation.tld) in ROOT_ZONE_TLDS
        )

    def normalize(self, notation: DomainNotation, contract: Contract) -> str:
        """Return the canonical A-label form shared by every rule."""
        return finalize(notation.labels)
