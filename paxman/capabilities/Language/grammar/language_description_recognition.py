"""Language description recognition — compositional ``<Language> in <Script/Region>``.

Custom ``recognize()`` on ``PipelineGrammar`` (BIC precedent): slot-filling
over three vocabularies with word-order variants fits no kernel matcher kind
(HOWTO Step 1 table). Declares the identity ``language_description``
semantics id (HOWTO Option B): the grammar emits display-valued slots and
performs no display→code mapping — meaning is assigned downstream by
``SectionIANARegistryDescription`` in
``rules/iana_language_subtag_registry_ed2026.py``, which maps slots via
``rules/data/description_display_map.py`` (+ the English-name authority map)
and validates the mapped codes against the shipped IANA sets.

Supported forms (full-phrase spans only — never bare-word spans):
  <Language> in <Script> [script]
  <Language> in <Region>
  <Region> <Language> in <Script> [script]
Parenthesized forms (``<Language> (<Script>, <Region>)``) stay deferred (#148).
A region prefix combines only with a script right side; with a region right
side the language-only inner phrase wins (``Singapore Chinese in Singapore``
yields the inner ``Chinese in Singapore`` span).

Phrase tokens must be whitespace-separated words: punctuation or alnum glue
between slots breaks the phrase (``Chinese-in-Singapore`` and ``Chinese2 in
Singapore`` are MISSING, not misread). Needs no suppression machinery of its
own: full-phrase spans never collide with the A0 whole-input exemption.

Separation: grammar tables stay key-only (``ENGLISH_LANGUAGE_KEYS``,
``SCRIPT_DISPLAY_KEYS``, ``REGION_DISPLAY_KEYS``); emitted fields carry the
matched normalized display keys verbatim, and ``compact`` joins those display
slots with hyphens (a display-joined carrier, never a canonical tag).
To extend coverage, add the key to the grammar/data key set AND its entry in
the rules/data authority map; ``test_data_consistency.py`` pins the pairing.
"""

from __future__ import annotations

import re

from paxman.capabilities.Language.grammar.data.english_names import (
    ENGLISH_LANGUAGE_KEYS,
)
from paxman.capabilities.Language.grammar.data.region_names import (
    REGION_DISPLAY_KEYS,
)
from paxman.capabilities.Language.grammar.data.script_names import (
    SCRIPT_DISPLAY_KEYS,
)
from paxman.capabilities.Language.notation import LanguageNotation, normalize_name
from paxman.core.domain import RecognitionMatch
from paxman.core.grammar import PipelineGrammar
from paxman.core.grammar.data.common_words import COMMON_WORDS

_TOKEN_RE = re.compile(r"[^\W\d_]+")
_WS_RE = re.compile(r"\s+")
_MAX_SLOT_TOKENS = 2


def _match_backward(
    raw: list[str], end: int, keys: frozenset[str]
) -> tuple[str, int] | None:
    """Longest normalized token run ending at ``end`` that is in ``keys``.

    Returns ``(key, start_index)`` or ``None``. Tries 2-token then 1-token.
    """
    for width in (_MAX_SLOT_TOKENS, 1):
        start = end - width
        if start < 0:
            continue
        key = normalize_name(" ".join(raw[start:end]))
        if key in keys:
            return (key, start)
    return None


def _match_forward(
    raw: list[str], start: int, keys: frozenset[str]
) -> tuple[str, int] | None:
    """Longest normalized token run starting at ``start`` in ``keys``.

    Returns ``(key, last_index)`` or ``None``. Tries 2-token then 1-token.
    """
    for width in (_MAX_SLOT_TOKENS, 1):
        end = start + width
        if end > len(raw):
            continue
        key = normalize_name(" ".join(raw[start:end]))
        if key in keys:
            return (key, end - 1)
    return None


def _gaps_are_whitespace(
    text: str, spans: list[tuple[int, int]], first: int, last: int
) -> bool:
    """Every gap between claimed tokens ``first..last`` is whitespace-only."""
    for k in range(first, last):
        gap = text[spans[k][1] : spans[k + 1][0]]
        if _WS_RE.fullmatch(gap) is None:
            return False
    return True


def _parse_at(
    text: str,
    raw: list[str],
    norm: list[str],
    spans: list[tuple[int, int]],
    sep: int,
) -> tuple[int, int, LanguageNotation] | None:
    """Parse one ``in`` separator at token ``sep`` into a full-phrase match."""
    n = len(raw)
    # Right side: script form (with optional trailing "script"), else region.
    script = ""
    region = ""
    last_idx = -1
    script_hit = _match_forward(raw, sep + 1, SCRIPT_DISPLAY_KEYS)
    script_closed = False
    if script_hit is not None:
        last_idx = script_hit[1]
        if last_idx + 1 < n and norm[last_idx + 1] == "script":
            last_idx += 1
            script_closed = True
        script = script_hit[0]
    else:
        region_hit = _match_forward(raw, sep + 1, REGION_DISPLAY_KEYS)
        if region_hit is None:
            return None
        last_idx = region_hit[1]
        region = region_hit[0]
    # Bare right side (script without its "script" word, or a region) must
    # not be followed by another content word: "traditional dress" is a
    # compound noun, not a description. Function words (COMMON_WORDS:
    # "and", "in", ...) may continue the sentence; a consumed "script"
    # word already closes the phrase.
    if (
        not script_closed
        and last_idx + 1 < n
        and norm[last_idx + 1] not in COMMON_WORDS
    ):
        return None
    # Left side: language ending at the separator, with an optional region
    # prefix only when the right side is a script ("<Region> <Language>
    # in <Script>"); a region right side takes the language-only inner span.
    lang_hit = _match_backward(raw, sep, ENGLISH_LANGUAGE_KEYS)
    if lang_hit is None:
        return None
    first_idx = lang_hit[1]
    if script:
        prefix_hit = _match_backward(raw, lang_hit[1], REGION_DISPLAY_KEYS)
        if prefix_hit is not None:
            region = prefix_hit[0]
            first_idx = prefix_hit[1]
    if not _gaps_are_whitespace(text, spans, first_idx, last_idx):
        return None
    start = spans[first_idx][0]
    end = spans[last_idx][1]
    language = lang_hit[0]
    pieces = [language]
    if script:
        pieces.append(script)
    if region:
        pieces.append(region)
    compact = "-".join(pieces)
    raw_text = text[start:end]
    notation = LanguageNotation(
        language=language,
        extlang="",
        script=script,
        region=region,
        variant="",
        extension="",
        privateuse="",
        grandfathered="",
        compact=compact,
        raw_value=raw_text.strip().lower(),
    )
    return (start, end, notation)


class LanguageDescriptionGrammar(PipelineGrammar[LanguageNotation]):
    """Compositional description recognition: ``<Language> in <Script/Region>``."""

    name = "language_description_recognition"
    semantics = "language_description"
    single_value = True

    def recognize(self, text: str) -> list[RecognitionMatch[LanguageNotation]]:
        """Slot-parse full-phrase descriptions; never bare-word spans."""
        if not text.strip():
            return []
        raw: list[str] = []
        spans: list[tuple[int, int]] = []
        for m in _TOKEN_RE.finditer(text):
            raw.append(m.group(0))
            spans.append((m.start(), m.end()))
        norm = [normalize_name(tok) for tok in raw]
        found: list[tuple[int, int, LanguageNotation]] = []
        for sep, word in enumerate(norm):
            if word != "in":
                continue
            parsed = _parse_at(text, raw, norm, spans, sep)
            if parsed is not None:
                found.append(parsed)
        # Deterministic longer-wins dedup for overlapping phrases.
        found.sort(key=lambda item: (item[0], -(item[1] - item[0])))
        kept: list[tuple[int, int, LanguageNotation]] = []
        for start, end, notation in found:
            if any(o_start <= start and end <= o_end for o_start, o_end, _ in kept):
                continue
            kept.append((start, end, notation))
        kept.sort(key=lambda item: (item[0], item[1]))
        return [
            RecognitionMatch(
                notation=notation,
                start=start,
                end=end,
                raw_text=text[start:end],
            )
            for start, end, notation in kept
        ]
