"""BIC recognition — 8 or 11 alphanum with optional BIC/SWIFT label."""

from __future__ import annotations

import re

from paxman.capabilities.BIC.grammar.data.country_codes import (
    COUNTRY_CODES as _COUNTRY_CODES,
)
from paxman.capabilities.BIC.notation import BICNotation
from paxman.core.domain import RecognitionMatch
from paxman.core.grammar.boundary import BoundaryGuard
from paxman.core.grammar.pipeline import PipelineGrammar
from paxman.core.grammar.stages import RegexStage, StandardPre

# Label separator is [\s:-]+ one or more, never zero width: a glued
# "BICDEUTDEFF" must not fuse into a mention (ISBN-13 precedent).
# Body is 4!c + 2!a + 2!c + optional 3!c = 8 or 11 only, never 9 or 10.
# (?ai:) ASCII restriction plus isascii filter rejects non ASCII like K.
# Grouped display: either compact (no spaces) or SWIFT paper form
# AAAA BB CC [XXX] with single spaces (#41). Double spaces stay MISSING;
# hybrid compact+spaced-branch (e.g. "DEUTDEFF now") is not grouped so
# trailing " now" stays separate word (fixes trailing_word test).
# Notation_fn strips via isalnum().
_BIC_COMPACT = r"[A-Z0-9]{4}[A-Z]{2}[A-Z0-9]{2}(?:[A-Z0-9]{3})?"
_BIC_GROUPED = r"[A-Z0-9]{4} [A-Z]{2} [A-Z0-9]{2}(?: [A-Z0-9]{3})?"
_BIC_BODY = (
    r"(?ai:(?:(?:BIC|SWIFT)[\s:-]+)?"
    rf"(?P<compact>(?:{_BIC_COMPACT}|{_BIC_GROUPED})))"
)
# word_only guards block left glue XDEUTDEFF and right glue DEUTDEFFY
# Negative lookahead blocks glued label without separator (BICDEUTDEFF, SWIFTDEUTDEFF).
# Only block when the suffix after BIC/SWIFT is itself a valid BIC shape
# with a valid country code, so compact 11-codes with a BIC-prefixed bank
# (e.g. BICXUS1AABC → bank BICX, country US) remain recognized (review).
# Country set is a generated projection from
# paxman/capabilities/BIC/rules/iso_9362_ed2022.COUNTRY_CODES
# (single source of truth — F8 / D10). Regenerate via
# tools/regenerate_bic_data.py; never hand-edit grammar/data/country_codes.py.
_COUNTRY_ALT = "|".join(sorted(_COUNTRY_CODES))
_BIC_SUFFIX_RE = f"[A-Z]{{4}}(?:{_COUNTRY_ALT})[A-Z0-9]{{2}}(?:[A-Z0-9]{{3}})?"
# Short English words that can trail a valid BIC as separate word
# (e.g. "DEUT DE FF at" — "at" is English, not extra BIC chars).
_COMMON_SHORT_WORDS = frozenset(
    {
        "a",
        "an",
        "at",
        "in",
        "on",
        "is",
        "as",
        "it",
        "to",
        "of",
        "by",
        "up",
        "so",
        "no",
        "my",
        "we",
        "be",
        "he",
        "if",
        "or",
        "am",
        "do",
        "go",
        "me",
        "us",
        "and",
        "but",
        "the",
        "for",
        "nor",
        "yet",
    }
)

# Words that can form false-positive BIC-like English phrases
# (e.g. "call me at" → CALLMEAT). Used to distinguish "deut de ff"
# (BIC) from "call me at" (English) when both are lower and grouped.
_ENGLISH_BIC_WORDS = frozenset(
    {
        "call",
        "me",
        "at",
        "time",
        "to",
        "go",
        "work",
        "by",
        "send",
        "please",
        "now",
        "today",
        "noon",
    }
)

_BIC_PATTERN = (
    BoundaryGuard.word_only().lookbehind
    + rf"(?!(?ai:(?:BIC|SWIFT){_BIC_SUFFIX_RE}\b))"
    + _BIC_BODY
    + BoundaryGuard.word_only().lookahead
)


def _bic_notation(match: re.Match[str]) -> BICNotation:
    raw_compact = match.group("compact")
    compact = "".join(ch for ch in raw_compact if ch.isascii() and ch.isalnum()).upper()
    bank_code = compact[0:4]
    country_code = compact[4:6]
    location_code = compact[6:8]
    branch_code = compact[8:11] if len(compact) == 11 else ""
    return BICNotation(
        bank_code=bank_code,
        country_code=country_code,
        location_code=location_code,
        branch_code=branch_code,
        compact=compact,
    )


class BICRecognitionGrammar(PipelineGrammar[BICNotation]):
    """BIC recognition — 8 or 11 alphanum with optional BIC/SWIFT label.

    Recognizes contiguous compact forms (``DEUTDEFF``) and SWIFT grouped
    display (``DEUT DE FF``, ``DEUT DE FF 500``, ``BNPA FR PP XXX``) with
    single spaces between the 4-2-2-3 groups; double spaces are not
    recognized. Case-insensitive; notation strips non-alnum.
    """

    name = "bic_recognition"
    semantics = "bic_recognition"
    single_value = True
    pre = StandardPre[BICNotation](empty_guard=True)
    regex = RegexStage[BICNotation](pattern=_BIC_PATTERN, notation_fn=_bic_notation)

    def recognize(self, text: str) -> list[RecognitionMatch[BICNotation]]:
        """Filter grouped 8 false positives and invalid 9/10.

        - Grouped 8 that looks like English phrase (e.g. "call me at")
          when followed by word is dropped.
        - Grouped 8 followed by double-space + alnum is always invalid
          (double spaces not allowed in grouped display).
        - Grouped 8 followed by single space + 1-2 alnum that is not a
          common short English word (e.g. " 5", " 50", " X") is
          considered invalid 9/10 and dropped; if trailing is a common
          English word like "at", "in", keep (valid BIC + trailing
          English word separate).
        """
        matches = super().recognize(text)
        filtered: list[RecognitionMatch[BICNotation]] = []
        for m in matches:
            raw_text = m.raw_text
            compact = m.notation.compact
            body_raw = re.sub(r"(?i)^(?:BIC|SWIFT)[\s:-]+", "", raw_text)
            is_grouped_8 = body_raw.count(" ") == 2 and len(compact) == 8
            if is_grouped_8:
                after = text[m.end :]
                # Double-space + alnum → always invalid for grouped
                if after.startswith("  ") and after.lstrip()[:1].isalnum():
                    continue
                # Single space + 1-2 alnum + not alnum → potential 9/10
                m_trailing = re.match(r" ([A-Za-z0-9]{1,2})(?![A-Za-z0-9])", after)
                if m_trailing:
                    trailing = m_trailing.group(1)
                    if trailing.lower() not in _COMMON_SHORT_WORDS:
                        continue
                # English phrase false positive: "call me at" etc.
                # Only drop if body looks like English (all words in
                # English sets) and is not upper (BIC is typically upper
                # but case-insensitive, so check lower)
                words = body_raw.split()
                if (
                    not body_raw.isupper()
                    and all(
                        w.lower() in _ENGLISH_BIC_WORDS
                        or w.lower() in _COMMON_SHORT_WORDS
                        for w in words
                    )
                    and after.startswith(" ")
                    and after.lstrip()[:1].isalnum()
                ):
                    continue
            filtered.append(m)
        return filtered
