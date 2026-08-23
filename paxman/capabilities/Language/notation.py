"""Language notation: grammar-normalized BCP 47 / bare code / name form."""

import re
import unicodedata
from dataclasses import dataclass


def normalize_name(name: str) -> str:
    """Normalize language display name for lexicon lookup.

    Mirrors Country normalize_name: NFKD decomposition, separator→space,
    alphanumeric-or-space filter, whitespace collapse, lower. Shared by
    grammar WholeInputLookup and rule views — do not duplicate.
    """
    nfkd = unicodedata.normalize("NFKD", name)
    without_accents = "".join(ch for ch in nfkd if not unicodedata.combining(ch))
    as_space = re.sub(r"[\"'’`._\-\u2010-\u2015]+", " ", without_accents)
    filtered = "".join(ch if ch.isalnum() or ch == " " else " " for ch in as_space)
    collapsed = " ".join(filtered.lower().split())
    return collapsed


@dataclass(frozen=True, slots=True)
class LanguageNotation:
    """Language normalized form.

    language primary subtag lower (2-8), or "" when grandfathered/privateuse-only.
    extlang hyphen-joined 3-letter extlangs or "".
    script 4-letter Title or "".
    region 2-letter Upper or 3-digit or "".
    variant hyphen-joined lower or "".
    extension hyphen-joined lower or "".
    privateuse "x-..." or "".
    grandfathered raw grandfathered lower or "".
    compact BCP 47 case-canonicalized tag or bare lower.
    raw_value original trimmed lower for lexicon.
    Grammar never validates registry; rules own it.
    """

    language: str
    extlang: str
    script: str
    region: str
    variant: str
    extension: str
    privateuse: str
    grandfathered: str
    compact: str
    raw_value: str
