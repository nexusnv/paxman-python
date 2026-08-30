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
_BIC_PATTERN = (
    BoundaryGuard.word_only().lookbehind
    + rf"(?!(?ai:(?:BIC|SWIFT){_BIC_SUFFIX_RE}\b))"
    + _BIC_BODY
    # block 8 inside 9/10 (single space+1-2) or double-space (#41)
    + r"(?!(?: [A-Za-z0-9]{1,2}(?![A-Za-z0-9])|  +[A-Za-z0-9]))"
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
        """Filter grouped 8 followed by word to avoid English false positives.

        Regex allows compact 8 + word (``DEUTDEFF now`` → ``DEUTDEFF``)
        but grouped 8 + word (``call me at noon`` → ``CALLMEAT``) would
        be a false positive (phrase mimics ``AAAA BB CC``). Drop only
        non-uppercase grouped 8 (English phrase) when followed by
        space+alnum; keep legitimate ``DEUT DE FF`` even with trailing
        word, and keep grouped 11 (``DEUT DE FF 500``) intact.
        """
        matches = super().recognize(text)
        filtered: list[RecognitionMatch[BICNotation]] = []
        for m in matches:
            raw_text = m.raw_text
            compact = m.notation.compact
            # Strip optional BIC/SWIFT label before counting spaces (#41)
            # so "BIC call me at noon" is correctly identified as grouped
            # 8 + trailing word, not as valid BIC with label.
            body_raw = re.sub(r"(?i)^(?:BIC|SWIFT)[\s:-]+", "", raw_text)
            if (
                body_raw.count(" ") == 2
                and len(compact) == 8
                and not body_raw.isupper()
            ):
                # Only drop non-uppercase grouped 8 (English phrase)
                # like "call me at"; keep "DEUT DE FF" with trailing
                # word.
                after = text[m.end : m.end + 4]
                if after.startswith(" ") and after.lstrip()[:1].isalnum():
                    continue
            filtered.append(m)
        return filtered
