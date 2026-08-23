"""IANA Language Subtag Registry validation.

Registry Type membership: language/script/region/variant + Prefix, Deprecated→Preferred,
private qaa-qtz + x- gated internally via include_private, grandfathered preferred.
"""

from __future__ import annotations

from paxman.capabilities.Language.notation import LanguageNotation
from paxman.capabilities.Language.rules.data.iana_deprecated_map import DEPRECATED_MAP
from paxman.capabilities.Language.rules.data.iana_grandfathered import (
    GRANDFATHERED_PREFERRED,
    GRANDFATHERED_TAGS,
)
from paxman.capabilities.Language.rules.data.iana_language_subtags import (
    IANA_LANGUAGE_SUBTAGS,
)
from paxman.capabilities.Language.rules.data.iana_region_subtags import (
    IANA_REGION_SUBTAGS,
)
from paxman.capabilities.Language.rules.data.iana_script_subtags import (
    IANA_SCRIPT_SUBTAGS,
)
from paxman.capabilities.Language.rules.data.iana_variant_subtags import (
    IANA_VARIANT_SUBTAGS,
    VARIANT_PREFIXES,
)
from paxman.core.contract import Contract
from paxman.core.domain import Provenance, Rule, RuleStrategy

PUBLICATION = Provenance(
    authority="IANA",
    specification_name="IANA Language Subtag Registry",
    kind="registry",
    reference_url="https://www.iana.org/assignments/language-subtag-registry/language-subtag-registry",
    version="Rolling File-Date 2026-08-08",
    lifecycle="active",
    publication_year=2026,
)

# Lower normalized sets for case-insensitive lookup
_LANGUAGE_SET = frozenset(s.lower() for s in IANA_LANGUAGE_SUBTAGS)
_SCRIPT_SET = frozenset(s.lower() for s in IANA_SCRIPT_SUBTAGS)
_REGION_SET = frozenset(s.lower() for s in IANA_REGION_SUBTAGS)
_VARIANT_SET = frozenset(s.lower() for s in IANA_VARIANT_SUBTAGS)


def _is_private_language(lang: str) -> bool:
    return "qaa" <= lang <= "qtz"


def _is_private_script(script: str) -> bool:
    # Qaaa is private script
    return script.lower() == "qaaa"


def _is_private_region(region: str) -> bool:
    # ZZ and XX are private region subtags for tests
    low = region.lower()
    return low in {
        "zz",
        "xx",
        "qm",
        "qn",
        "qo",
        "qp",
        "qq",
        "qr",
        "qs",
        "qt",
        "qu",
        "qv",
        "qw",
        "qx",
        "qy",
        "qz",
    }


def _resolve_deprecated(lang: str) -> str:
    seen: set[str] = set()
    cur = lang.lower()
    while cur in DEPRECATED_MAP and cur not in seen:
        seen.add(cur)
        cur = DEPRECATED_MAP[cur].lower()
    return cur


class SectionIANARegistry(Rule[LanguageNotation]):
    """IANA Registry — language/script/region/variant membership plus constraints."""

    name = "Section-iana-registry"
    strategy = RuleStrategy.LOOKUP_TABLE
    provenance = PUBLICATION
    citation = (
        "IANA Registry Type language/script/region/variant "
        "Deprecated Preferred Prefix Suppress-Script"
    )
    target_semantics = frozenset({"bcp47_tag"})
    requires_features = frozenset()

    def matches(self, notation: LanguageNotation, contract: Contract) -> bool:
        """Validate registry membership with private and prefix constraints."""
        include_private = bool(getattr(contract, "include_private", False))

        # Grandfathered
        if notation.grandfathered:
            return notation.grandfathered.lower() in GRANDFATHERED_TAGS

        # Privateuse-only
        if notation.privateuse:
            return bool(include_private)

        # Language
        lang = notation.language.lower() if notation.language else ""
        if lang:
            if _is_private_language(lang):
                if not include_private:
                    return False
            else:
                # Check deprecated or direct membership
                resolved = _resolve_deprecated(lang)
                if lang in DEPRECATED_MAP:
                    pass
                elif lang not in _LANGUAGE_SET and resolved not in _LANGUAGE_SET:
                    return False

        # Extlang
        if notation.extlang:
            for ext in notation.extlang.lower().split("-"):
                if not ext:
                    continue
                if _is_private_language(ext):
                    if not include_private:
                        return False
                elif ext not in _LANGUAGE_SET:
                    return False

        # Script
        if notation.script:
            scr = notation.script
            if _is_private_script(scr):
                if not include_private:
                    return False
            elif scr.lower() not in _SCRIPT_SET:
                return False

        # Region
        if notation.region:
            reg = notation.region
            if _is_private_region(reg):
                if not include_private:
                    return False
            elif reg.lower() not in _REGION_SET and not (
                reg.isdigit() and reg.lower() in _REGION_SET
            ):
                return False

        # Variant + Prefix
        if notation.variant:
            for var in notation.variant.lower().split("-"):
                if not var:
                    continue
                if var not in _VARIANT_SET:
                    return False
                prefixes = VARIANT_PREFIXES.get(var)
                if prefixes is not None:
                    lower_compact = notation.compact.lower()
                    idx = lower_compact.rfind("-" + var)
                    prefix = lower_compact[:idx] if idx != -1 else lang
                    allowed = frozenset(p.lower() for p in prefixes)
                    if prefix not in allowed and lang not in allowed:
                        candidates = {lang}
                        if notation.script:
                            candidates.add(f"{lang}-{notation.script.lower()}")
                        if notation.region:
                            candidates.add(f"{lang}-{notation.region.lower()}")
                            if notation.script:
                                candidates.add(
                                    f"{lang}-{notation.script.lower()}"
                                    f"-{notation.region.lower()}"
                                )
                        if notation.extlang:
                            candidates.add(f"{lang}-{notation.extlang.lower()}")
                        if not candidates & allowed and prefix not in allowed:
                            return False

        return not (notation.privateuse and not include_private)

    def normalize(self, notation: LanguageNotation, contract: Contract) -> str:
        """Return canonical tag with Deprecated and grandfathered preferred."""
        # Grandfathered preferred
        if notation.grandfathered:
            low = notation.grandfathered.lower()
            return GRANDFATHERED_PREFERRED.get(low, low)

        # Privateuse-only
        if notation.privateuse and not notation.language:
            return notation.privateuse.lower()

        parts: list[str] = []
        lang = notation.language.lower() if notation.language else ""
        if lang:
            lang = _resolve_deprecated(lang)
            parts.append(lang)
        if notation.extlang:
            # Each extlang resolved? Keep as is
            for ext in notation.extlang.lower().split("-"):
                if ext:
                    parts.append(_resolve_deprecated(ext))
        if notation.script:
            # Title case
            s = notation.script
            parts.append(s[0].upper() + s[1:].lower() if s else "")
        if notation.region:
            r = notation.region
            if r.isdigit():
                parts.append(r)
            else:
                parts.append(r.upper())
        if notation.variant:
            for var in notation.variant.lower().split("-"):
                if var:
                    parts.append(var.lower())
        if notation.extension:
            for ext in notation.extension.lower().split("-"):
                if ext:
                    parts.append(ext)
        if notation.privateuse:
            # privateuse is "x-..." already lower
            parts.extend(notation.privateuse.lower().split("-"))

        # Handle case where language was deprecated and we already resolved
        # Reassemble
        if not parts:
            return notation.compact
        # Preserve hyphen joins
        # Language already lower, script title, region upper handled
        return "-".join(parts)
