"""BIC recognition — 8 or 11 alphanum with optional BIC/SWIFT label."""

from __future__ import annotations

import re

from paxman.capabilities.BIC.grammar.data.country_codes import (
    COUNTRY_CODES as _COUNTRY_CODES,
)
from paxman.capabilities.BIC.notation import BICNotation
from paxman.core.domain import RecognitionMatch
from paxman.core.grammar.boundary import BoundaryGuard
from paxman.core.grammar.data.common_words import COMMON_WORDS
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
# Derived from COMMON_WORDS (paxman.core.grammar.data.common_words, 67):
# the 19 legacy words present there form the derived subset; the 12-word
# remainder below holds legacy words absent from COMMON_WORDS (single letter
# "a"; 2-letter "go"/"if"/"of"/"on"/"up"/"we" outside the Google-1000 ∩ ISO
# intersection; longer "but"/"for"/"nor"/"the"/"yet") kept to preserve
# behavior. The union is exactly the legacy 31-word set (zero delta — the
# pin below plus the existing suites prove no behavior change beyond the
# #106 end-of-text/punctuation arm).
_COMMON_SHORT_FROM_COMMON_WORDS = frozenset(
    w
    for w in COMMON_WORDS
    if w
    in {
        "am",
        "an",
        "and",
        "as",
        "at",
        "be",
        "by",
        "do",
        "he",
        "in",
        "is",
        "it",
        "me",
        "my",
        "no",
        "or",
        "so",
        "to",
        "us",
    }
)
_COMMON_SHORT_REMAINDER = frozenset(
    {"a", "but", "for", "go", "if", "nor", "of", "on", "the", "up", "we", "yet"}
)
_COMMON_SHORT_WORDS = _COMMON_SHORT_FROM_COMMON_WORDS | _COMMON_SHORT_REMAINDER
assert (
    frozenset(
        {
            "a",
            "am",
            "an",
            "and",
            "as",
            "at",
            "be",
            "but",
            "by",
            "do",
            "for",
            "go",
            "he",
            "if",
            "in",
            "is",
            "it",
            "me",
            "my",
            "no",
            "nor",
            "of",
            "on",
            "or",
            "so",
            "the",
            "to",
            "up",
            "us",
            "we",
            "yet",
        }
    )
    == _COMMON_SHORT_WORDS
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
                # but case-insensitive, so check lower). The isupper gate
                # stays per Slice B decision 5: CALL ME AT keeps status quo.
                # Drop when followed by a word (#41) or when the phrase
                # ends here: end of text, punctuation-only tail (#106),
                # or any other non-alphanumeric lead — parentheses,
                # brackets, dashes. The all-English membership gate above
                # still protects real BICs.
                words = body_raw.split()
                after_stripped = after.lstrip()
                phrase_ends_here = (
                    (after.startswith(" ") and after_stripped[:1].isalnum())
                    or after.strip(" .,:;!?\t\n\r") == ""
                    or (after_stripped[:1] != "" and not after_stripped[:1].isalnum())
                )
                if (
                    not body_raw.isupper()
                    and all(
                        w.lower() in _ENGLISH_BIC_WORDS
                        or w.lower() in _COMMON_SHORT_WORDS
                        for w in words
                    )
                    and phrase_ends_here
                ):
                    continue
            filtered.append(m)
        return filtered
