"""IANA Language Subtag Registry validation.

Registry Type membership: language/script/region/variant + Prefix,
Deprecated→Preferred, grandfathered preferred. Private-use reservations
are validated by the engine-gated private rule
``SectionIANARegistryPrivate``; generic rejects private.
"""

from __future__ import annotations

from paxman.capabilities.Language.notation import LanguageNotation, normalize_name
from paxman.capabilities.Language.rules.data.description_display_map import (
    DESCRIPTION_DISPLAY_MAP,
)
from paxman.capabilities.Language.rules.data.english_language_map import (
    NAME_TO_CANONICAL,
)
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

# Normalized display-name views — keys normalized via the shared normalizer.
# Language display meaning reuses the English-name authority map (the same
# table backing SectionEnglishNameMapping; duplicating its 60 entries here
# would create dual authority). Script/region display meaning comes from the
# compositional authority map (single source of truth, shared with the
# consistency test — never mirrored into grammar code).
_NAME_TO_CANONICAL_NORMALIZED: dict[str, str] = {
    normalize_name(k): v for k, v in NAME_TO_CANONICAL.items()
}
_DISPLAY_TO_SUBTAG_NORMALIZED: dict[str, str] = {
    normalize_name(k): v for k, v in DESCRIPTION_DISPLAY_MAP.items()
}

# Lower normalized sets for case-insensitive lookup
_LANGUAGE_SET = frozenset(s.lower() for s in IANA_LANGUAGE_SUBTAGS)
_SCRIPT_SET = frozenset(s.lower() for s in IANA_SCRIPT_SUBTAGS)
_REGION_SET = frozenset(s.lower() for s in IANA_REGION_SUBTAGS)
_VARIANT_SET = frozenset(s.lower() for s in IANA_VARIANT_SUBTAGS)


def _is_private_language(lang: str) -> bool:
    """Return True when the language subtag is private-use qaa-qtz."""
    return "qaa" <= lang <= "qtz"


def _is_private_script(script: str) -> bool:
    """Return True when the script subtag is private-use Qaaa-Qabx."""
    low = script.lower()
    return "qaaa" <= low <= "qabx"


def _is_private_region(region: str) -> bool:
    """Return True when the region subtag is a private-use reservation."""
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
        "xx",
        "xy",
        "xz",
    }


def _resolve_deprecated(lang: str) -> str:
    """Follow the deprecated map chain to the preferred subtag."""
    seen: set[str] = set()
    cur = lang.lower()
    while cur in DEPRECATED_MAP and cur not in seen:
        seen.add(cur)
        cur = DEPRECATED_MAP[cur].lower()
    return cur


def _has_no_other_components(notation: LanguageNotation) -> bool:
    """Return True when only a privateuse slot is populated."""
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
    """IANA Registry — language/script/region/variant membership (non-private)."""

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

        if not has_private:
            return False

        # Validate preceding components with generic checks, allowing private
        if lang and not _is_private_language(lang):
            resolved = _resolve_deprecated(lang)
            if (
                lang not in DEPRECATED_MAP
                and lang not in _LANGUAGE_SET
                and resolved not in _LANGUAGE_SET
            ):
                return False
        if notation.extlang:
            for ext in notation.extlang.lower().split("-"):
                if not ext or _is_private_language(ext):
                    continue
                if ext not in _LANGUAGE_SET:
                    return False
        if (
            notation.script
            and not _is_private_script(notation.script)
            and notation.script.lower() not in _SCRIPT_SET
        ):
            return False
        if (
            notation.region
            and not _is_private_region(notation.region)
            and notation.region.lower() not in _REGION_SET
            and not (
                notation.region.isdigit() and notation.region.lower() in _REGION_SET
            )
        ):
            return False
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


class SectionIANARegistryDescription(Rule[LanguageNotation]):
    """IANA Registry — compositional display descriptions (language_description).

    Same publication as ``SectionIANARegistry`` (one file per publication):
    maps the grammar's display-valued slots to canonical subtags — language
    via the English-name authority map, script/region via
    ``description_display_map`` — then validates the mapped codes against the
    shipped IANA language/script/region sets and normalizes to the canonical
    tag (``chinese`` + ``traditional`` + ``singapore`` → ``zh-Hant-SG``).
    Unknown display slots yield no match (MISSING upstream when the grammar
    emits nothing else for the span).
    """

    name = "Section-iana-registry-description"
    strategy = RuleStrategy.LOOKUP_TABLE
    provenance = PUBLICATION
    citation = (
        "IANA Registry Type language/script/region "
        "via display-name mapping (English names + description_display_map)"
    )
    target_semantics = frozenset({"language_description"})
    requires_features = frozenset()

    def _resolve(self, notation: LanguageNotation) -> tuple[str, str, str] | None:
        """Map display slots to canonical subtags, or ``None`` when unmapped."""
        # Description semantics carry display slots only: any BCP 47 structural
        # field (extlang/variant/extension/privateuse/grandfathered) means this
        # notation is not a description.
        if (
            notation.extlang
            or notation.variant
            or notation.extension
            or notation.privateuse
            or notation.grandfathered
        ):
            return None
        lang_key = normalize_name(notation.language) if notation.language else ""
        lang = _NAME_TO_CANONICAL_NORMALIZED.get(lang_key)
        if lang is None:
            return None
        script = ""
        if notation.script:
            mapped_script = _DISPLAY_TO_SUBTAG_NORMALIZED.get(
                normalize_name(notation.script)
            )
            if mapped_script is None:
                return None
            script = mapped_script
        region = ""
        if notation.region:
            mapped_region = _DISPLAY_TO_SUBTAG_NORMALIZED.get(
                normalize_name(notation.region)
            )
            if mapped_region is None:
                return None
            region = mapped_region
        # A bare language display without a script/region qualifier is the
        # language_name grammar's domain, not a description.
        if not script and not region:
            return None
        return (lang, script, region)

    def matches(self, notation: LanguageNotation, contract: Contract) -> bool:
        """Validate mapped codes against the shipped IANA sets (non-private)."""
        resolved = self._resolve(notation)
        if resolved is None:
            return False
        lang, script, region = resolved
        if _is_private_language(lang):
            return False
        resolved_lang = _resolve_deprecated(lang)
        if (
            lang not in DEPRECATED_MAP
            and lang not in _LANGUAGE_SET
            and resolved_lang not in _LANGUAGE_SET
        ):
            return False
        if script:
            if _is_private_script(script):
                return False
            if script.lower() not in _SCRIPT_SET:
                return False
        if region:
            if _is_private_region(region):
                return False
            if region.lower() not in _REGION_SET and not (
                region.isdigit() and region.lower() in _REGION_SET
            ):
                return False
        return True

    def normalize(self, notation: LanguageNotation, contract: Contract) -> str:
        """Return the canonical tag assembled from the mapped subtags.

        Unmapped input falls back to ``compact``; unreachable in-pipeline
        (the engine normalizes only notations ``matches()`` accepted) —
        defensive, since rules never raise.
        """
        resolved = self._resolve(notation)
        if resolved is None:
            return notation.compact
        lang, script, region = resolved
        parts: list[str] = [_resolve_deprecated(lang)]
        if script:
            parts.append(script[0].upper() + script[1:].lower() if script else "")
        if region:
            if region.isdigit():
                parts.append(region)
            else:
                parts.append(region.upper())
        return "-".join(parts)
