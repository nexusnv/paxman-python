"""IANA Language Subtag Registry — Deprecated → Preferred-Value chain.

Source: IANA Language Subtag Registry
Reference: https://www.iana.org/assignments/language-subtag-registry/language-subtag-registry
File-Date: 2026-08-08
Deprecated subtags with Preferred-Value; chain includes historical codes.

Language subtags only. The registry also deprecates *region* subtags
(``BU`` → ``MM``, ``YD`` → ``YE``), but ISO 3166 region deprecations belong
to the Country capability's authority and must never be mirrored here: a
language rule reading them emits a country code (E2).

Separation: authority-backed tables serving rules only.
"""

from __future__ import annotations

DEPRECATED_MAP: dict[str, str] = {
    # Language subtags
    "iw": "he",
    "in": "id",
    "ji": "yi",
    "jw": "jv",
    "mo": "ro",
    "bh": "bih",
    "scc": "sr",
    "scr": "hr",
    "mol": "ro",
    "bod": "bo",
    "ces": "cs",
    "cym": "cy",
    "deu": "de",
    "dzo": "dz",
    "eus": "eu",
    "fas": "fa",
    "fra": "fr",
    "hye": "hy",
    "isl": "is",
    "kat": "ka",
    "kor": "ko",
    "mya": "my",
    "nld": "nl",
    "ron": "ro",
    "slk": "sk",
    "sqi": "sq",
    "zho": "zh",
}
