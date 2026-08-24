"""IANA Language Subtag Registry validation.

Registry Type membership: language/script/region/variant + Prefix,
Deprecated→Preferred, grandfathered preferred. Private-use reservations
are validated by the engine-gated private rule
``SectionIANARegistryPrivate``; generic rejects private.
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
    low = script.lower()
    return "qaaa" <= low <= "qabx"


def _is_private_region(region: str) -> bool:
    low = region.lower()
    return low in {
        "aa",
        "zz",
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
        "xa",
        "xb",
        "xc",
        "xd",
        "xe",
        "xf",
        "xg",
        "xh",
        "xi",
        "xj",
        "xk",
        "xl",
        "xm",
        "xn",
        "xo",
        "xp",
        "xq",
        "xr",
        "xs",
        "xt",
        "xu",
        "xv",
        "xw",
        "xy",
        "xz",
    }


def _resolve_deprecated(lang: str) -> str:
    seen: set[str] = set()
    cur = lang.lower()
    while cur in DEPRECATED_MAP and cur not in seen:
        seen.add(cur)
        cur = DEPRECATED_MAP[cur].lower()
    return cur


def _has_no_other_components(notation: LanguageNotation) -> bool:
    return not (
        notation.language
        or notation.extlang
        or notation.script
        or notation.region
        or notation.variant
        or notation.extension
        or notation.grandfathered
    )


class SectionIANARegistry(Rule[LanguageNotation]):
    """IANA Registry — language/script/region/variant membership (non-private)."""  # noqa: E501

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
        """Validate registry membership (private subtags invalid)."""
        # Grandfathered
        if notation.grandfathered:
            return notation.grandfathered.lower() in GRANDFATHERED_TAGS

        # Privateuse-only: generic rejects
        if notation.privateuse and _has_no_other_components(notation):
            return False

        # If any private subtag present → invalid for generic
        if notation.privateuse:
            # privateuse suffix with other components → invalid for generic
            return False

        # Language
        lang = notation.language.lower() if notation.language else ""
        if lang:
            if _is_private_language(lang):
                return False
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
                    return False
                if ext not in _LANGUAGE_SET:
                    return False

        # Script
        if notation.script:
            scr = notation.script
            if _is_private_script(scr):
                return False
            if scr.lower() not in _SCRIPT_SET:
                return False

        # Region
        if notation.region:
            reg = notation.region
            if _is_private_region(reg):
                return False
            if reg.lower() not in _REGION_SET and not (
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

        return True

    def normalize(self, notation: LanguageNotation, contract: Contract) -> str:
        """Return canonical tag with Deprecated and grandfathered preferred."""
        if notation.grandfathered:
            low = notation.grandfathered.lower()
            return GRANDFATHERED_PREFERRED.get(low, low)

        if notation.privateuse and not notation.language:
            return notation.privateuse.lower()

        parts: list[str] = []
        lang = notation.language.lower() if notation.language else ""
        if lang:
            lang = _resolve_deprecated(lang)
            parts.append(lang)
        if notation.extlang:
            for ext in notation.extlang.lower().split("-"):
                if ext:
                    parts.append(_resolve_deprecated(ext))
        if notation.script:
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
            parts.extend(notation.privateuse.lower().split("-"))

        if not parts:
            return notation.compact
        return "-".join(parts)


class SectionIANARegistryPrivate(Rule[LanguageNotation]):
    """IANA Registry — private-use reservations (engine-gated)."""

    name = "Section-iana-registry-private"
    strategy = RuleStrategy.LOOKUP_TABLE
    provenance = PUBLICATION
    citation = "IANA Registry private-use qaa-qtz/Qaaa-Qabx/QM-QZ/AA/XA-XZ/ZZ/x-"
    target_semantics = frozenset({"bcp47_tag"})
    requires_features = frozenset({"include_private"})

    def matches(self, notation: LanguageNotation, contract: Contract) -> bool:
        """Validate private-use reservations when include_private."""
        if notation.grandfathered:
            return notation.grandfathered.lower() in GRANDFATHERED_TAGS

        if notation.privateuse and _has_no_other_components(notation):
            return True

        has_private = False
        lang = notation.language.lower() if notation.language else ""
        if lang and _is_private_language(lang):
            has_private = True
        if notation.extlang:
            for ext in notation.extlang.lower().split("-"):
                if ext and _is_private_language(ext):
                    has_private = True
        if notation.script and _is_private_script(notation.script):
            has_private = True
        if notation.region and _is_private_region(notation.region):
            has_private = True
        if notation.privateuse:
            has_private = True

        return has_private

    def normalize(self, notation: LanguageNotation, contract: Contract) -> str:
        """Return canonical tag (same as generic)."""
        if notation.grandfathered:
            low = notation.grandfathered.lower()
            return GRANDFATHERED_PREFERRED.get(low, low)
        if notation.privateuse and not notation.language:
            return notation.privateuse.lower()
        parts: list[str] = []
        lang = notation.language.lower() if notation.language else ""
        if lang:
            lang = _resolve_deprecated(lang)
            parts.append(lang)
        if notation.extlang:
            for ext in notation.extlang.lower().split("-"):
                if ext:
                    parts.append(_resolve_deprecated(ext))
        if notation.script:
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
            parts.extend(notation.privateuse.lower().split("-"))
        if not parts:
            return notation.compact
        return "-".join(parts)
