"""Brand IIN/length membership — Section 1 brand prefix (gated secondary)."""

from __future__ import annotations

import re

from paxman.capabilities.CreditCard.notation import PANNotation
from paxman.capabilities.CreditCard.rules.data.brand_prefix import BRAND_PREFIXES
from paxman.core.contract import Contract
from paxman.core.domain import Provenance, Rule, RuleStrategy

PUBLICATION = Provenance(
    authority="Brand networks",
    specification_name="Brand IIN/length tables (secondary)",
    kind="registry",
    reference_url="https://en.wikipedia.org/wiki/Payment_card_number",
    version="Rolling 2026",
    lifecycle="active",
    publication_year=2026,
)

# Mirrors the grammar charset (defense-in-depth, ISIN precedent).
_PAN_RE = re.compile(r"^[0-9]{12,19}$")


def _luhn_valid(digits: str) -> bool:
    """Validate a digit string with modulus 10 Double-Add-Double.

    Local copy of the ISO rule's accumulator (copy-never-import, ISIN/GTIN
    precedent): intentional ADR-0012 corroboration, never a waiver — this
    rule duplicates Luhn so it can never contradict the ISO rule's verdict.
    """
    total = 0
    for index, digit in enumerate(reversed(digits)):
        value = ord(digit) - 48
        if index % 2 == 1:
            value *= 2
            if value > 9:
                value -= 9
        total += value
    return total % 10 == 0


def matching_brands(digits: str) -> frozenset[str]:
    """Brands whose prefix interval and length allowlist match ``digits``.

    Membership only — several brands may match (CUP co-brand Discover
    ranges), an empty set means "no allowlisted brand".
    """
    if not isinstance(digits, str) or not digits.isascii() or not digits.isdigit():
        return frozenset()
    length = len(digits)
    hits: set[str] = set()
    for brand, (intervals, lengths) in BRAND_PREFIXES.items():
        if length not in lengths:
            continue
        for start, end, width in intervals:
            if length >= width and start <= int(digits[:width]) <= end:
                hits.add(brand)
                break
    return frozenset(hits)


class Section1BrandPrefixMembership(Rule[PANNotation]):
    """Secondary brand IIN/length membership (gated by include_brand_validation).

    Validates that the PAN's leading digits and length fall inside an
    allowlisted brand range, after re-checking structure and Luhn (local
    copies — ADR-0012 corroboration, never a waiver of the ISO rule).
    """

    name = "Section 1-brand-prefix-membership"
    strategy = RuleStrategy.LOOKUP_TABLE
    provenance = PUBLICATION
    citation = (
        "Section 1 (brand prefix membership; secondary brand specs "
        "authoritative per-network)"
    )
    target_semantics = frozenset({"pan_recognition"})
    requires_features = frozenset({"include_brand_validation"})

    def matches(self, notation: PANNotation, contract: Contract) -> bool:
        """Check whether the PAN matches an allowlisted brand prefix."""
        digits = notation.digits
        compact = notation.compact
        if not isinstance(digits, str) or not isinstance(compact, str):
            return False
        if compact != digits:
            return False
        if _PAN_RE.match(digits) is None:
            return False
        if not _luhn_valid(digits):
            return False
        return bool(matching_brands(digits))

    def normalize(self, notation: PANNotation, contract: Contract) -> str:
        """Normalize to the compact digit string."""
        return notation.digits
