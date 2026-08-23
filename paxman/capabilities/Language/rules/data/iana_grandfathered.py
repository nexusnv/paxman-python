"""IANA Language Subtag Registry — Type: grandfathered.

Source: IANA Language Subtag Registry
Reference: https://www.iana.org/assignments/language-subtag-registry/language-subtag-registry
File-Date: 2026-08-08
Type: grandfathered 26 entries (17 irregular + 9 regular), all Deprecated.

Separation: authority-backed tables serving rules only.
"""

from __future__ import annotations

# 26 grandfathered tags (lowercase canonical)
GRANDFATHERED_TAGS: frozenset[str] = frozenset(
    {
        "en-gb-oed",
        "i-ami",
        "i-bnn",
        "i-default",
        "i-enochian",
        "i-hak",
        "i-klingon",
        "i-lux",
        "i-mingo",
        "i-navajo",
        "i-pwn",
        "i-tao",
        "i-tay",
        "i-tsu",
        "sgn-be-fr",
        "sgn-be-nl",
        "sgn-ch-de",
        "art-lojban",
        "cel-gaulish",
        "no-bok",
        "no-nyn",
        "zh-guoyu",
        "zh-hakka",
        "zh-min",
        "zh-min-nan",
        "zh-xiang",
        "i-cherokee",
    }
)

# Preferred-Value mapping for deprecated grandfathered (lower → preferred canonical)
GRANDFATHERED_PREFERRED: dict[str, str] = {
    "en-gb-oed": "en-GB-oxendict",
    "i-ami": "ami",
    "i-bnn": "bnn",
    "i-default": "en",
    "i-enochian": "enochian",
    "i-hak": "hak",
    "i-klingon": "tlh",
    "i-lux": "lb",
    "i-mingo": "see",
    "i-navajo": "nv",
    "i-pwn": "pwn",
    "i-tao": "tao",
    "i-tay": "tay",
    "i-tsu": "tsu",
    "sgn-be-fr": "sfb",
    "sgn-be-nl": "vgt",
    "sgn-ch-de": "sgg",
    "art-lojban": "jbo",
    "cel-gaulish": "cel-gaulish",
    "no-bok": "nb",
    "no-nyn": "nn",
    "zh-guoyu": "cmn",
    "zh-hakka": "hak",
    "zh-min": "nan",
    "zh-min-nan": "nan",
    "zh-xiang": "hsn",
    "i-cherokee": "chr",
}
