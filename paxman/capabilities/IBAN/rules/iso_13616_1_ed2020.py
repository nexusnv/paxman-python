"""ISO 13616-1:2020 + ISO/IEC 7064:2003 MOD 97-10 — generic IBAN structure.

ISO 13616-1:2020 Section 4 (Structure) defines IBAN as 2-letter country code
(ISO 3166-1 alpha-2, must be in SWIFT IBAN Registry) + 2 check digits + BBAN
(1-30 alphanum, country-specific). Section 5 normatively references
ISO/IEC 7064:2003 MOD 97-10 for the checksum: rearrange BBAN+CC+"00",
expand A=10 … Z=35, then (98 - mod97) are check digits, validation requires
mod97(compact rearranged) == 1. Check digits 02-98 are valid (00/01/99
never yield mod97==1 and are rejected explicitly).

The SWIFT IBAN Registry (Release 99 Dec 2024, mirrors R100 Oct 2025,
mirrored at https://www.iban.com/structure 8 May 2026 — 111 country rows)
provides per-country fixed lengths and the CC allowlist used here. The 111
include AO (Angola) and West/Central African jurisdictions added in 2024;
FP (French Polynesia) is not an IBAN country (under FR) and was removed
from the prior 90-code stub. Lengths are authoritative per-country fixed
values (e.g. DE22, GB22, SA24, NO15, MT31, LC32, RU33, BE16).
"""

from __future__ import annotations

from paxman.capabilities.IBAN.notation import IBANNotation
from paxman.capabilities.IBAN.rules.data.iban_registry import (
    IBAN_LENGTHS,
    REGISTERED_IBAN_COUNTRY_CODES,
)
from paxman.core.contract import Contract
from paxman.core.domain import Provenance, Rule, RuleStrategy

PUBLICATION = Provenance(
    authority="ISO",
    specification_name="ISO 13616-1:2020",
    kind="specification",
    reference_url="https://www.iso.org/standard/81090.html",
    version="2020",
    lifecycle="active",
    publication_year=2020,
)

# Legacy re-export for tests that import from this module; prefer
# paxman.capabilities.IBAN.rules.data.iban_registry directly.
# Kept for backwards compatibility of the audit test suite.
# (Will be removed when tests migrate to the data module.)
# pylint: disable=unused-import

_REGISTERED_IBAN_COUNTRY_CODES = REGISTERED_IBAN_COUNTRY_CODES
_IBAN_LENGTHS = IBAN_LENGTHS


def _mod97(compact: str) -> int:
    rearranged = compact[4:] + compact[:4]
    expanded_chars: list[str] = []
    for ch in rearranged:
        if "A" <= ch <= "Z":
            expanded_chars.append(str(ord(ch) - 55))
        else:
            expanded_chars.append(ch)
    expanded = "".join(expanded_chars)
    r = 0
    for d in expanded:
        r = (r * 10 + int(d)) % 97
    return r


class Section4IBANStructureMOD97(Rule[IBANNotation]):
    """ISO 13616-1 §4-5 + ISO/IEC 7064 MOD 97-10 — generic IBAN validation.

    Validates IBAN: total 15-34, charset [A-Z]{2}[0-9]{2}[A-Z0-9]{1,30},
    CC in SWIFT IBAN Registry (111 codes as of R99/R100 May 2026),
    per-country fixed length (e.g. DE22, NO15), DD in 02-98 (reject
    00/01/99), and mod97==1. Citations: ISO 13616-1:2020 structure + MOD
    97-10 normative reference to ISO/IEC 7064:2003; CC check against SWIFT
    IBAN Registry (via iban.com mirror 8 May 2026). Per-country lengths are
    enforced before mod97 — wrong-length IBAN with correct mod97 is INVALID.
    """

    name = "Section 4-iban-structure-mod97"
    strategy = RuleStrategy.PARSER
    provenance = PUBLICATION
    citation = "Section 4-5 (structure + MOD 97-10, via ISO/IEC 7064:2003)"
    target_semantics = frozenset({"iban_recognition"})
    requires_features = frozenset()

    def matches(self, notation: IBANNotation, contract: Contract) -> bool:
        c = notation.compact
        if not (15 <= len(c) <= 34):
            return False
        if not c.isascii() or not c.isalnum() or not c.isupper():
            return False
        if not (c[0:2].isalpha() and c[2:4].isdigit()):
            return False
        if c[0:2] not in REGISTERED_IBAN_COUNTRY_CODES:
            return False
        # Per-country fixed length from SWIFT IBAN Registry (authoritative).
        # Generic 15-34 is outer bound; country-specific length is exact.
        expected = IBAN_LENGTHS.get(c[0:2])
        if expected is not None and len(c) != expected:
            return False
        if c[2:4] in ("00", "01", "99"):
            return False
        return _mod97(c) == 1

    def normalize(self, notation: IBANNotation, contract: Contract) -> str:
        return notation.compact
