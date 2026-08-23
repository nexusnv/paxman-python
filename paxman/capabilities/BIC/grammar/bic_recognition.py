"""BIC recognition — 8 or 11 alphanum with optional BIC/SWIFT label."""

from __future__ import annotations

import re

from paxman.capabilities.BIC.notation import BICNotation
from paxman.core.grammar.boundary import BoundaryGuard
from paxman.core.grammar.pipeline import PipelineGrammar
from paxman.core.grammar.stages import RegexStage, StandardPre

# Label separator is [\s:-]+ one or more, never zero width: a glued
# "BICDEUTDEFF" must not fuse into a mention (ISBN-13 precedent).
# Body is 4!c + 2!a + 2!c + optional 3!c = 8 or 11 only, never 9 or 10.
# (?ai:) ASCII restriction plus isascii filter rejects non ASCII like K.
_BIC_BODY = (
    r"(?ai:(?:(?:BIC|SWIFT)[\s:-]+)?"
    r"(?P<compact>[A-Z0-9]{4}[A-Z]{2}[A-Z0-9]{2}(?:[A-Z0-9]{3})?))"
)
# word_only guards block left glue XDEUTDEFF and right glue DEUTDEFFY
# Negative lookahead blocks glued label without separator (BICDEUTDEFF, SWIFTDEUTDEFF)
_BIC_PATTERN = (
    BoundaryGuard.word_only().lookbehind
    + r"(?!(?ai:(?:BIC|SWIFT)[A-Z0-9]))"
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
    """BIC recognition — 8 or 11 alphanum with optional BIC/SWIFT label."""

    name = "bic_recognition"
    semantics = "bic_recognition"
    single_value = True
    pre = StandardPre[BICNotation](empty_guard=True)
    regex = RegexStage[BICNotation](pattern=_BIC_PATTERN, notation_fn=_bic_notation)
