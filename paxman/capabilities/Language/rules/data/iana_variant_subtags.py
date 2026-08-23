"""IANA Language Subtag Registry — Type: variant.

Source: IANA Language Subtag Registry
Reference: https://www.iana.org/assignments/language-subtag-registry/language-subtag-registry
File-Date: 2026-08-08
Type: variant records ~80+; curated subset plus Prefix constraint table.

Separation: authority-backed tables serving rules only.
"""

from __future__ import annotations

IANA_VARIANT_SUBTAGS: frozenset[str] = frozenset(
    {
        "1901",
        "1994",
        "1996",
        "abl1943",
        "alalc97",
        "aluku",
        "arevela",
        "arevmda",
        "bakan",
        "balanka",
        "barla",
        "biske",
        "boont",
        "fonipa",
        "fonupa",
        "fonxsamp",
        "heploc",
        "hognorsk",
        "jyutping",
        "kkcor",
        "kocor",
        "lipaw",
        "nedis",
        "njiva",
        "oxendict",
        "pinyin",
        "polyton",
        "rozaj",
        "scouse",
        "tarask",
        "ucrcor",
        "ulster",
        "unifon",
        "valencia",
        "wadegile",
    }
)

# Prefix constraint: variant → allowed prefixes (language or language-Tag prefix)
# e.g., nedis prefix must contain tag prefix sl, de-nedis rejected
VARIANT_PREFIXES: dict[str, frozenset[str]] = {
    "nedis": frozenset({"sl"}),
    "1996": frozenset({"de", "sl"}),
    "oxendict": frozenset({"en-gb"}),
    "1901": frozenset({"de"}),
    "1994": frozenset({"sl-rozaj", "sl"}),
    "alalc97": frozenset({"ru"}),
    "fonipa": frozenset({"en", "de", "fr", "sl"}),
    "pinyin": frozenset({"zh"}),
    "wadegile": frozenset({"zh"}),
    "rozaj": frozenset({"sl"}),
    "biske": frozenset({"sl"}),
}
