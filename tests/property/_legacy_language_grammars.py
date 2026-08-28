"""Verbatim legacy Language BCP47 grammar (pre-scanner migration).

Snapshot of the bespoke ``_BCP47RegexStage`` + ``_bcp47_notation`` logic at
the start of B3a (841c0a7), used by the Migration Proof Harness
(ADR-0009 §9.3) to assert byte-identical ``RecognitionMatch`` output after
the scanner migration. Classes are renamed ``Legacy*`` to avoid colliding.

Do NOT edit by hand — this is a frozen reference. The live grammar files are
the source of truth post-migration; this module exists only so the parity
test can compare old vs new behavior.
"""

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

_GRANDFATHERED_SET: frozenset[str] = _GRANDFATHERED_TAGS_SET
_GRANDFATHERED_ALT = "|".join(
    re.escape(t) for t in sorted(_GRANDFATHERED_TAGS_SET, key=lambda t: (-len(t), t))
)

_BCP47_BODY = (
    r"(?P<tag>" + _GRANDFATHERED_ALT + r"|x(?:-[A-Za-z0-9]{1,8})+"
    r"|(?:(?=[A-Za-z]{2,8}-)"
    r"(?:[A-Za-z]{2,3}(?:-[A-Za-z]{3}){0,3}|[A-Za-z]{4}|[A-Za-z]{5,8})"
    r"(?:-[A-Za-z]{4})?"
    r"(?:-(?:[A-Za-z]{2}|\d{3}))?"
    r"(?:-(?:[A-Za-z0-9]{5,8}|\d[A-Za-z0-9]{3}))*"
    r"(?:-[A-WY-Za-wy-z](?:-[A-Za-z0-9]{2,8})+)*"
    r"(?:-x(?:-[A-Za-z0-9]{1,8})+)?"
    r")"
    r")"
)

_GUARD = BoundaryGuard.word_only()
_BCP47_PATTERN = _GUARD.lookbehind + _BCP47_BODY + _GUARD.lookahead


def _is_variant(subtag: str) -> bool:
    return (5 <= len(subtag) <= 8 and subtag.isalnum()) or (
        len(subtag) == 4 and subtag[0].isdigit() and subtag[1:].isalnum()
    )


def _bcp47_notation(match: re.Match[str]) -> LanguageNotation:
    raw_tag: str = match.group("tag")
    lower_tag = raw_tag.lower()
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
    parts = raw_tag.split("-")
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
    while idx < len(parts):
        sub = parts[idx]
        if sub.lower() == "x":
            privateuse = "-".join(p.lower() for p in parts[idx:])
            idx = len(parts)
            break
        if len(sub) == 1 and sub.isalnum() and sub.lower() != "x":
            break
        if _is_variant(sub):
            variant_parts.append(sub.lower())
            idx += 1
            continue
        break
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
                if parts[idx].lower() == "x" and len(parts[idx]) == 1:
                    break
                ext_subtags.append(parts[idx].lower())
                idx += 1
            if ext_subtags:
                extension_parts.append(singleton + "-" + "-".join(ext_subtags))
            else:
                extension_parts.append(singleton)
            continue
        break
    variant = "-".join(variant_parts)
    extension = "-".join(extension_parts)
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


class LegacyBCP47TagGrammar(PipelineGrammar[LanguageNotation]):
    """Legacy BCP47 tag recognition — verbatim."""

    name = "bcp47_tag_recognition"
    semantics = "bcp47_tag"
    single_value = True

    pre = StandardPre[LanguageNotation](empty_guard=True)
    regex = _BCP47RegexStage(
        pattern=_BCP47_PATTERN,
        notation_fn=_bcp47_notation,
        flags=re.IGNORECASE,
    )
