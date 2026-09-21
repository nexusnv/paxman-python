"""ANNA ISIN Guidelines Section 5 — country and special prefix."""

from __future__ import annotations

from paxman.capabilities.ISIN.notation import ISINNotation
from paxman.capabilities.ISIN.rules.data.country_codes import (
    ISO_3166_1_ALPHA_2,
    SPECIAL_PREFIXES,
)
from paxman.core.contract import Contract
from paxman.core.domain import Provenance, Rule, RuleStrategy

PUBLICATION = Provenance(
    authority="ANNA",
    specification_name="ANNA ISIN Guidelines",
    kind="policy",
    reference_url=(
        "https://anna-web.org/wp-content/uploads/2025/11/"
        "ISIN-Guidelines-Dec-2025_Amendment_clean.pdf"
    ),
    version="2025-12 (V25; superseded by V26 Jun 2026)",
    lifecycle="active",
    publication_year=2025,
)

# Accepted two-letter prefixes: ISO 3166-1 alpha-2 plus the ANNA special
# prefixes. Per-prefix attestation strength lives in rules/data/country_codes.py:
# Guidelines-attested EU/XS/XA-XD/XT, RA-attested EZ, validator and
# user-assigned XF/XK/QS/QT. ZZ is provisional and excluded from v1.
_VALID_PREFIXES: frozenset[str] = ISO_3166_1_ALPHA_2 | SPECIAL_PREFIXES


def _expand(compact: str) -> str:
    """Expand each character to its numeric value (digits stay, A=10 ... Z=35)."""
    parts: list[str] = []
    for ch in compact:
        if "0" <= ch <= "9":
            parts.append(ch)
        else:
            parts.append(str(ord(ch) - 55))
    return "".join(parts)


def _luhn_valid(expanded: str) -> bool:
    """Validate an expanded digit string with modulus 10 Double-Add-Double."""
    total = 0
    for index, digit in enumerate(reversed(expanded)):
        value = ord(digit) - 48
        if index % 2 == 1:
            value *= 2
            if value > 9:
                value -= 9
        total += value
    return total % 10 == 0


class Section5CountryAndSpecialPrefix(Rule[ISINNotation]):
    """ANNA ISIN Guidelines Section 5 — country and special prefix.

    Validates that the two-letter prefix is an ISO 3166-1 alpha-2 code or
    an attested ANNA special prefix (XS/EU/EZ/XT/XA-XD/XF/XK/QS/QT).
    """

    name = "Section 5-country-and-special-prefix"
    strategy = RuleStrategy.LOOKUP_TABLE
    provenance = PUBLICATION
    citation = "Prefix vocabulary (ISO 3166-1 alpha-2 plus special prefixes)"
    target_semantics = frozenset({"isin_recognition"})
    requires_features = frozenset()

    def matches(self, notation: ISINNotation, contract: Contract) -> bool:
        # Prefix membership plus the ISO 6166 check digit. The duplicate
        # check is intentional (ISBN Section 4.2-gs1-prefix audit-B3
        # precedent): ADR-0012 corroboration is one-directional — LOOKUP_TABLE
        # candidates always survive — so a prefix-only lookup would let a
        # checksum-broken input with a valid prefix through as SUCCESS via
        # this rule alone. Both provenances stay independently attributable.
        if notation.country_code not in _VALID_PREFIXES:
            return False
        compact = notation.compact
        if len(compact) != 12 or not compact[:2].isalpha():
            return False
        if not compact[2:11].isalnum() or not compact[11].isdigit():
            return False
        return _luhn_valid(_expand(compact))

    def normalize(self, notation: ISINNotation, contract: Contract) -> str:
        return notation.compact
