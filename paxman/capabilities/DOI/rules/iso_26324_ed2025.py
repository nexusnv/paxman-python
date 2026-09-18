"""ISO 26324:2025 rules: DOI name syntax (structure only, no checksum).

The DOI system itself makes no use of check digits (Handbook §4.3.5,
PDF-confirmed — deliberate, with per-application exceptions such as
EIDR's suffix-only check char that this PARSER accepts structurally
and never validates). Prefix shape + '/' + non-empty quoteless suffix
is the entire authority check; unallocated-but-shaped prefixes read
SUCCESS (storable, UUID precedent).
"""

from __future__ import annotations

import re

from paxman.capabilities.DOI.notation import DOINotation
from paxman.core.contract import Contract
from paxman.core.domain import Provenance, Rule, RuleStrategy

PUBLICATION = Provenance(
    authority="ISO",
    specification_name="ISO 26324",
    kind="specification",
    reference_url="https://www.iso.org/standard/88862.html",
    version="2025",
    lifecycle="active",
    publication_year=2025,
)

# Registrant bound 4-9 digits per P1793/scholid/Gilmartin consensus, with
# the dotted sub-registrant tail per Handbook §4.3.2.
_PREFIX_RE = re.compile(r"10\.[0-9]{4,9}(?:\.[0-9]+)*")
# Suffix rejects whitespace and the Wikidata-quoteless exclusions
# ('"'/'&'/'''); interior dots/slashes retained (opaque suffix).
_FORBIDDEN_SUFFIX_RE = re.compile(r"[\"&'\s]")


class Section4DOISyntax(Rule[DOINotation]):
    """Section 4-doi-syntax: prefix shape + '/' + non-empty suffix."""

    name = "Section 4-doi-syntax"
    strategy = RuleStrategy.PARSER
    provenance = PUBLICATION
    citation = "Section 4 (DOI name syntax: prefix/suffix)"
    target_semantics = frozenset({"doi_recognition"})
    requires_features = frozenset()

    def matches(self, notation: DOINotation, contract: Contract) -> bool:
        """True when the prefix shape holds and the suffix is non-empty."""
        try:
            return (
                _PREFIX_RE.fullmatch(notation.prefix) is not None
                and len(notation.suffix) > 0
                and _FORBIDDEN_SUFFIX_RE.search(notation.suffix) is None
                # Graphic-type only (Handbook §4.3.1): reject non-printable
                # code points such as NUL (Cc) or U+200B (Cf) while keeping
                # valid printable Unicode (é, CJK, emoji) accepted.
                and notation.suffix.isprintable()
            )
        except (TypeError, AttributeError):
            return False

    def normalize(self, notation: DOINotation, contract: Contract) -> str:
        """Return the ASCII-folded bare prefix/suffix canonical form."""
        try:
            return notation.canonical
        except AttributeError:
            return ""
