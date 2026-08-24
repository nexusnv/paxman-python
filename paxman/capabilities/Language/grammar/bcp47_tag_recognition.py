"""BCP 47 tag recognition — ABNF-approximate with underscore tolerance."""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass, field

from paxman.capabilities.Language.grammar.data.grandfathered_tags import (
    GRANDFATHERED_TAGS as _GRANDFATHERED_TAGS_SET,
)
from paxman.capabilities.Language.notation import LanguageNotation
from paxman.core.domain import RecognitionMatch
from paxman.core.grammar.boundary import BoundaryGuard
from paxman.core.grammar.pipeline import PipelineGrammar
from paxman.core.grammar.stages import PipelineState, StandardPre

# ---------------------------------------------------------------------------
# Grandfathered enumerated alternation (27 tags: 26 authority + i-cherokee test vector)
# IANA Language Subtag Registry File-Date 2026-08-08 + test vector i-cherokee
# Generated source: paxman/capabilities/Language/grammar/data/grandfathered_tags.py
# ---------------------------------------------------------------------------
_GRANDFATHERED_SET: frozenset[str] = _GRANDFATHERED_TAGS_SET
_GRANDFATHERED_ALT = "|".join(
    re.escape(t) for t in sorted(_GRANDFATHERED_TAGS_SET, key=lambda t: (-len(t), t))
)

# ---------------------------------------------------------------------------
# ABNF-approximate BCP 47 body — hyphen only (underscore via Pre scratch)
# language ["-" script] ["-" region] *("-" variant) *("-" extension) ["-" privateuse]
# plus grandfathered and x-privateuse
# Bare language alone (e.g. "en") is NOT a BCP47 tag here — that is the
# language_code grammar's domain. Require hyphen after language in first
# branch so bare codes route strictly to language_code.
# Grandfathered first — prevents truncation of en-GB-oed to en-GB.
# ---------------------------------------------------------------------------
_BCP47_BODY = (
    r"(?P<tag>" + _GRANDFATHERED_ALT + r"|x(?:-[A-Za-z0-9]{1,8})+"  # privateuse-only
    r"|(?:(?=[A-Za-z]{2,3}-)"
    r"[A-Za-z]{2,3}(?:-[A-Za-z]{3}){0,3}"
    r"(?:-[A-Za-z]{4})?"  # script
    r"(?:-(?:[A-Za-z]{2}|\d{3}))?"  # region
    r"(?:-(?:[A-Za-z0-9]{5,8}|\d[A-Za-z0-9]{3}))*"  # variant
    r"(?:-[0-9A-WY-Za-wy-z](?:-[A-Za-z0-9]{2,8})+)*"  # extension (singleton != x)
    r"(?:-x(?:-[A-Za-z0-9]{1,8})+)?"  # privateuse tail
    r")"
    r")"
)

_GUARD = BoundaryGuard.word_only()
_BCP47_PATTERN = _GUARD.lookbehind + _BCP47_BODY + _GUARD.lookahead


def _is_variant(subtag: str) -> bool:
    """Return True if subtag matches variant ABNF: 5*8alphanum | DIGIT 3alphanum."""
    return (5 <= len(subtag) <= 8 and subtag.isalnum()) or (
        len(subtag) == 4 and subtag[0].isdigit() and subtag[1:].isalnum()
    )


def _bcp47_notation(match: re.Match[str]) -> LanguageNotation:
    raw_tag: str = match.group("tag")
    # raw_tag is from normalized text (hyphens), preserve case for raw handling
    lower_tag = raw_tag.lower()

    # Grandfathered
    if lower_tag in _GRANDFATHERED_SET:
        return LanguageNotation(
            language="",
            extlang="",
            script="",
            region="",
            variant="",
            extension="",
            privateuse="",
            grandfathered=lower_tag,
            compact=lower_tag,
            raw_value=lower_tag,
        )

    # Privateuse-only
    if lower_tag.startswith("x-") or lower_tag == "x":
        compact = lower_tag
        return LanguageNotation(
            language="",
            extlang="",
            script="",
            region="",
            variant="",
            extension="",
            privateuse=compact,
            grandfathered="",
            compact=compact,
            raw_value=lower_tag,
        )

    # Langtag — split and infer by position/length
    parts = raw_tag.split("-")
    # parts are from normalized hyphenated tag
    language = parts[0].lower()
    idx = 1
    extlangs: list[str] = []
    if len(language) in (2, 3):
        while (
            idx < len(parts)
            and len(parts[idx]) == 3
            and parts[idx].isalpha()
            and len(extlangs) < 3
        ):
            extlangs.append(parts[idx].lower())
            idx += 1
    extlang = "-".join(extlangs)

    script = ""
    if idx < len(parts) and len(parts[idx]) == 4 and parts[idx].isalpha():
        # Title case
        s = parts[idx]
        script = s[0].upper() + s[1:].lower()
        idx += 1

    region = ""
    if idx < len(parts) and (
        (len(parts[idx]) == 2 and parts[idx].isalpha())
        or (len(parts[idx]) == 3 and parts[idx].isdigit())
    ):
        region = parts[idx].upper() if parts[idx].isalpha() else parts[idx]
        idx += 1

    variant_parts: list[str] = []
    extension_parts: list[str] = []
    privateuse = ""

    # Collect variants before extensions
    while idx < len(parts):
        sub = parts[idx]
        # Detect privateuse start
        if sub.lower() == "x":
            # privateuse consumes rest
            privateuse = "-".join(p.lower() for p in parts[idx:])
            idx = len(parts)
            break
        # Detect extension singleton (single alphanum != x)
        if len(sub) == 1 and sub.isalnum() and sub.lower() != "x":
            # Extension start — break variant collection
            break
        if _is_variant(sub):
            variant_parts.append(sub.lower())
            idx += 1
            continue
        # If sub is not variant and not extension/privateuse, it is unexpected
        # but for robustness treat as variant if 5-8? already handled,
        # else break to extension handling
        break

    # Collect extensions: one or more singleton + 2-8 alphanum runs
    while idx < len(parts):
        sub = parts[idx]
        if sub.lower() == "x":
            privateuse = "-".join(p.lower() for p in parts[idx:])
            idx = len(parts)
            break
        if len(sub) == 1 and sub.isalnum() and sub.lower() != "x":
            singleton = sub.lower()
            idx += 1
            ext_subtags: list[str] = []
            while (
                idx < len(parts) and 2 <= len(parts[idx]) <= 8 and parts[idx].isalnum()
            ):
                # Stop if next is x privateuse singleton?
                if parts[idx].lower() == "x" and len(parts[idx]) == 1:
                    break
                # Also stop if next singleton would start? Singleton is
                # 1 char, we already handle 2-8 check, so 1 char won't match
                ext_subtags.append(parts[idx].lower())
                idx += 1
            if ext_subtags:
                extension_parts.append(singleton + "-" + "-".join(ext_subtags))
            else:
                # Malformed extension — keep singleton alone
                extension_parts.append(singleton)
            continue
        # If not extension singleton nor privateuse, and we are in extension section,
        # any remaining variant-like subtags would have been handled earlier;
        # break to avoid infinite loop
        break

    # Privateuse already handled above if present

    variant = "-".join(variant_parts)
    extension = "-".join(extension_parts)

    # Assemble compact case-canonical
    compact_pieces: list[str] = []
    compact_pieces.append(language)
    if extlang:
        compact_pieces.extend(extlang.split("-"))
    if script:
        compact_pieces.append(script)
    if region:
        compact_pieces.append(region)
    if variant:
        compact_pieces.extend(variant.split("-"))
    if extension:
        compact_pieces.extend(extension.split("-"))
    if privateuse:
        compact_pieces.extend(privateuse.split("-"))

    compact = "-".join(compact_pieces)
    raw_value = lower_tag

    return LanguageNotation(
        language=language,
        extlang=extlang,
        script=script,
        region=region,
        variant=variant,
        extension=extension,
        privateuse=privateuse,
        grandfathered="",
        compact=compact,
        raw_value=raw_value,
    )


@dataclass(frozen=True, slots=True)
class _BCP47RegexStage:
    """Regex stage with underscore→hyphen scratch handling, preserving raw_text."""

    pattern: str
    notation_fn: Callable[[re.Match[str]], LanguageNotation] | None = None
    flags: int = 0
    _compiled: re.Pattern[str] = field(init=False, repr=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "_compiled", re.compile(self.pattern, self.flags))

    def run(
        self, state: PipelineState[LanguageNotation]
    ) -> PipelineState[LanguageNotation]:
        if self.notation_fn is None:
            return state
        # Underscore tolerance: scan normalized text but emit raw_text from original
        original = state.text
        normalized = original.replace("_", "-")
        new_matches: list[RecognitionMatch[LanguageNotation]] = list(state.matches)
        for m in self._compiled.finditer(normalized):
            start = m.start()
            end = m.end()
            raw_text = original[start:end]
            notation = self.notation_fn(m)
            new_matches.append(
                RecognitionMatch(
                    notation=notation,
                    start=start,
                    end=end,
                    raw_text=raw_text,
                )
            )
        return PipelineState(
            text=state.text, matches=new_matches, scratch=dict(state.scratch)
        )


class BCP47TagGrammar(PipelineGrammar[LanguageNotation]):
    """BCP47 tag recognition — ABNF-approximate with underscore tolerance."""

    name = "bcp47_tag_recognition"
    semantics = "bcp47_tag"
    single_value = True

    pre = StandardPre[LanguageNotation](empty_guard=True)
    regex = _BCP47RegexStage(
        pattern=_BCP47_PATTERN,
        notation_fn=_bcp47_notation,
        flags=re.IGNORECASE,
    )
