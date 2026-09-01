"""RFC 5952 IPv6 text representation rule — validates and normalizes IPv6."""

from __future__ import annotations

import ipaddress

from paxman.capabilities.IP.notation import IPNotation
from paxman.core.contract import Contract
from paxman.core.domain import Provenance, Rule, RuleStrategy

PUBLICATION = Provenance(
    authority="IETF",
    specification_name="RFC 5952",
    kind="specification",
    reference_url="https://datatracker.ietf.org/doc/html/rfc5952",
    version="2010",
    lifecycle="active",
    publication_year=2010,
)


class Section4IPv6TextRepresentation(Rule[IPNotation]):
    """RFC 5952 Section 4 — A Recommendation for IPv6 Text Representation.

    Validates IPv6 addresses and normalizes to the recommended compressed
    form: lowercase hex, :: for the longest zero run, no leading zeros
    except for the :: itself. The underlying 128-bit architecture and the
    embedded-IPv4 ``LS32`` form (``::ffff:192.0.2.1``) are defined in
    RFC 4291 §2.2; RFC 5952 §5 recommends the same compressed rendering for
    mixed addresses and is honored by :class:`ipaddress.IPv6Address`.
    """

    name = "Section 4-ipv6-text-representation"
    strategy = RuleStrategy.PARSER
    provenance = PUBLICATION
    citation = "Section 4 (IPv6 text representation)"
    target_semantics = frozenset({"ipv6_recognition"})
    requires_features = frozenset()

    def matches(self, notation: IPNotation, contract: Contract) -> bool:
        """Check if the address is a valid IPv6 address."""
        try:
            addr = ipaddress.IPv6Address(notation.address)
            return addr.version == 6
        except ValueError:
            return False

    def normalize(self, notation: IPNotation, contract: Contract) -> str:
        """Normalize to RFC 5952 recommended compressed form.

        The ipaddress module's str() output follows RFC 5952:
        - Lowercase hex digits
        - :: for the longest run of consecutive zeros
        - No leading zeros in groups
        """
        try:
            addr = ipaddress.IPv6Address(notation.address)
            return str(addr)
        except ValueError:
            return notation.address
