"""ISIN recognition — 12-char CC+NSIN+C with optional ISIN label."""

from __future__ import annotations

import re

from paxman.capabilities.ISIN.notation import ISINNotation
from paxman.core.grammar.boundary import BoundaryGuard
from paxman.core.grammar.pipeline import PipelineGrammar
from paxman.core.grammar.stages import RegexStage, StandardPre

# Label separator is [\s:-]+ one-or-more, never zero-width: a glued
# "ISINUS0378331005" must not fuse into a mention (ISBN-13/IBAN/BIC precedent).
# Body: CC + 9 alnum + 1 digit = exactly 12, never 11 or 13.
# Single-space tolerance is interleaved ((?: ?[A-Z0-9]){9} ?[0-9]) so attested
# groupings ("US 037833 100 5", "US037833 1005", "PL0000 503132") match while
# double spaces stay MISSING; the fixed count prevents unbounded absorption.
# (?ai:) ASCII restriction rejects fullwidth digits and non-ASCII homoglyphs
# while BoundaryGuard.word_only() stays Unicode-aware (no global re.ASCII).
_ISIN_BODY = (
    r"(?:(?ai:ISIN)[\s:-]+)?"
    r"(?P<compact>(?ai:[A-Z]{2}(?: ?[A-Z0-9]){9} ?[0-9]))"
)
# Glued-label guard: block only when what follows literal "ISIN" is itself a
# complete valid-shape ISIN (mirrors shipped BIC grammar review note); genuine
# Iceland codes ("IS" + NSIN starting with digits) are unaffected because the
# suffix after "ISIN" then starts with a digit, not [A-Z]{2}.
_GLUED_LABEL_GUARD = r"(?!(?ai:ISIN[A-Z]{2}[A-Z0-9]{9}[0-9]))"
_ISIN_PATTERN = (
    BoundaryGuard.word_only().lookbehind
    + _GLUED_LABEL_GUARD
    + _ISIN_BODY
    + BoundaryGuard.word_only().lookahead
)


def _isin_notation(match: re.Match[str]) -> ISINNotation:
    raw_compact = match.group("compact")
    compact = "".join(ch for ch in raw_compact if ch.isascii() and ch.isalnum()).upper()
    # compact is now exactly 12 alphanum ending in a digit; split structurally
    return ISINNotation(
        country_code=compact[0:2],
        nsin=compact[2:11],
        check_digit=compact[11],
        compact=compact,
    )


class ISINRecognitionGrammar(PipelineGrammar[ISINNotation]):
    """ISIN recognition — 12-char CC+NSIN+C, optional label, spaces."""

    name = "isin_recognition"
    semantics = "isin_recognition"
    single_value = True
    pre = StandardPre[ISINNotation](empty_guard=True)
    regex = RegexStage[ISINNotation](
        pattern=_ISIN_PATTERN, notation_fn=_isin_notation, flags=re.IGNORECASE
    )


# Scaffolder seam: capability.py imports ISINRecognition; keep it an alias.
ISINRecognition = ISINRecognitionGrammar
