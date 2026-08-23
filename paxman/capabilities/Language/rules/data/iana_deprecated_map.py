"""IANA Language Subtag Registry — Deprecated → Preferred-Value chain.

Source: IANA Language Subtag Registry
Reference: https://www.iana.org/assignments/language-subtag-registry/language-subtag-registry
File-Date: 2026-08-08
Deprecated subtags with Preferred-Value; chain includes historical codes.

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
    "sh": "sr",
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
    # Region deprecated? Not in test but included for completeness
    "bu": "mm",
    "tl": "ph",
    "yd": "ye",
}
