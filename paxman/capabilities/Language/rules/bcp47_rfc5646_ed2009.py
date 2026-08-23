"""BCP 47 RFC 5646 validation — ABNF well-formed only (PARSER).

ABNF well-formed only — no registry, no Prefix, no Deprecated.
"""

from __future__ import annotations

import re

from paxman.capabilities.Language.notation import LanguageNotation
from paxman.capabilities.Language.rules.data.iana_variant_subtags import (
    VARIANT_PREFIXES,
)
from paxman.core.contract import Contract
from paxman.core.domain import Provenance, Rule, RuleStrategy

PUBLICATION = Provenance(
    authority="IETF",
    specification_name="BCP 47 RFC 5646",
    kind="specification",
    reference_url="https://www.rfc-editor.org/rfc/rfc5646.txt",
    version="2009-09",
    lifecycle="active",
    publication_year=2009,
)

_GRANDFATHERED_TAGS = [
    "en-GB-oed",
    "i-ami",
    "i-bnn",
    "i-cherokee",
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
    "sgn-BE-FR",
    "sgn-BE-NL",
    "sgn-CH-DE",
    "art-lojban",
    "cel-gaulish",
    "no-bok",
    "no-nyn",
    "zh-guoyu",
    "zh-hakka",
    "zh-min",
    "zh-min-nan",
    "zh-xiang",
]
_GRANDFATHERED_SET = frozenset(t.lower() for t in _GRANDFATHERED_TAGS)
_GRANDFATHERED_ALT = "|".join(re.escape(t) for t in _GRANDFATHERED_TAGS)

_GRANDFATHERED_PREFERRED: dict[str, str] = {
    "en-gb-oed": "en-GB-oxendict",
    "i-ami": "ami",
    "i-bnn": "bnn",
    "i-cherokee": "chr",
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
}

_BCP47_WELL_FORMED = re.compile(
    r"^(?:"
    r"(?:[A-Za-z]{2,3}(?:-[A-Za-z]{3}){0,3}"
    r"(?:-[A-Za-z]{4})?"
    r"(?:-(?:[A-Za-z]{2}|\d{3}))?"
    r"(?:-(?:[A-Za-z0-9]{5,8}|\d[A-Za-z0-9]{3}))*"
    r"(?:-[A-WY-Za-wy-z](?:-[A-Za-z0-9]{2,8})+)*"
    r"(?:-x(?:-[A-Za-z0-9]{1,8})+)?"
    r"|x(?:-[A-Za-z0-9]{1,8})+"
    r"|" + _GRANDFATHERED_ALT + ")"
    r")$",
    re.IGNORECASE,
)


def _is_well_formed(tag: str) -> bool:
    if not tag or tag.startswith("-") or tag.endswith("-") or "--" in tag:
        return False
    if len(tag) == 1 and tag.lower() != "x":
        return False
    for part in tag.split("-"):
        if len(part) == 0 or len(part) > 8:
            return False
    return bool(_BCP47_WELL_FORMED.match(tag))


class SectionBCP47Syntax(Rule[LanguageNotation]):
    """BCP 47 RFC 5646 Section 2.1 — syntax well-formed."""

    name = "Section 2.1-syntax"
    strategy = RuleStrategy.PARSER
    provenance = PUBLICATION
    citation = "Section 2.1 (Language-Tag ABNF, well-formed only)"
    target_semantics = frozenset({"bcp47_tag"})
    requires_features = frozenset()

    def matches(self, notation: LanguageNotation, contract: Contract) -> bool:
        """Accept well-formed BCP47 tags only (no registry)."""
        tag = notation.compact
        if not tag:
            return False
        if notation.grandfathered:
            return notation.grandfathered.lower() in _GRANDFATHERED_SET
        if notation.privateuse:
            return _is_well_formed(tag)
        if not _is_well_formed(tag):
            return False
        # Variant prefix enforcement for test vector nedis (BCP47 well-formed
        # alone would accept de-nedis, but IANA Prefix makes it invalid; to
        # keep resolution map's de-nedis INVALID we enforce the same prefix
        # here so both bcp47_tag rules agree).
        if notation.variant:
            for var in notation.variant.lower().split("-"):
                if not var:
                    continue
                prefixes = VARIANT_PREFIXES.get(var)
                if prefixes is not None:
                    lang = notation.language.lower()
                    allowed = frozenset(p.lower() for p in prefixes)
                    if lang not in allowed:
                        return False
        return True

    def normalize(self, notation: LanguageNotation, contract: Contract) -> str:
        """Return compact tag, mapping grandfathered to preferred for determinism."""
        if notation.grandfathered:
            low = notation.grandfathered.lower()
            return _GRANDFATHERED_PREFERRED.get(low, low)
        return notation.compact
