"""LEI recognition — 20-char LOU+entity+check with label and URN carrier."""

from __future__ import annotations

import re

from paxman.capabilities.LEI.notation import LEINotation
from paxman.core.grammar.boundary import BoundaryGuard
from paxman.core.grammar.pipeline import PipelineGrammar
from paxman.core.grammar.stages import RegexStage, StandardPre

# Module-scope string pattern — compiled by RegexStage (never inside
# recognize()). Core: 18 alphanum + a 2-digit check tail = exactly 20 payload
# chars, never 19 or 21. The ISIN single-trailing-digit shape does NOT
# transfer: LEI has TWO check digits, so the tail is (?: ?[0-9]){2}, not a
# lone ?[0-9] — the latter claims 19 chars and, under word_only().lookahead,
# matches nothing. Single-space interleave (ISIN precedent) tolerates
# attested spacing while the fixed count bounds absorption; double
# spaces/tabs stay MISSING. Label separator is [\s:-]+ one-or-more, never
# zero-width: a glued "LEI5493000..." must not fuse into a mention (ISIN/ORCID
# precedent). URN carrier is the IANA-registered `urn:lei:` form, optional and
# case-insensitive (GLEIF namespace: "not case sensitive").
# (?ai:) ASCII restriction rejects fullwidth digits and non-ASCII homoglyphs
# while BoundaryGuard.word_only() stays Unicode-aware (no global re.ASCII).
_LEI_CORE = r"(?ai:[A-Z0-9](?: ?[A-Z0-9]){17}(?: ?[0-9]){2})"
_LEI_BODY = (
    r"(?:(?ai:LEI)[\s:-]+)?"
    r"(?:(?ai:urn:lei:))?"
    rf"(?P<compact>{_LEI_CORE})"
)
# Glued-label guard: fires only when a COMPLETE 20-char LEI shape follows
# literal "LEI" with no separator ("LEI5493..." = 23+ chars), mirroring ISIN's
# full-shape _GLUED_LABEL_GUARD. Two traps avoided: a one-alnum guard would
# reject a bare LEI whose own prefix starts "LEI", and putting "urn:lei:" in
# the guard makes the carrier branch unreachable — the carrier is correct
# glued form, not glue; a carrier-inclusive guard fires exactly when the
# branch would match and truncates the span to "lei:...". Length separates
# the two cases: glued label = 3 + 20 chars, bare code = 20.
_LEI_GLUED_GUARD = r"(?!(?ai:LEI[A-Z0-9]{18}[0-9]{2}))"
_LEI_PATTERN = (
    BoundaryGuard.word_only().lookbehind
    + _LEI_GLUED_GUARD
    + _LEI_BODY
    + BoundaryGuard.word_only().lookahead
)


def _lei_notation(match: re.Match[str]) -> LEINotation:
    raw_compact = match.group("compact")
    compact = "".join(ch for ch in raw_compact if ch.isascii() and ch.isalnum()).upper()
    # compact is now exactly 20 alphanum ending in 2 digits; split structurally
    return LEINotation(
        lou_prefix=compact[0:4],
        entity_block=compact[4:18],
        check_digits=compact[18:20],
        compact=compact,
    )


class LEIRecognitionGrammar(PipelineGrammar[LEINotation]):
    """LEI recognition — compact 20-char with optional label and URN carrier."""

    name = "lei_recognition"
    semantics = "lei_recognition"
    single_value = True
    pre = StandardPre[LEINotation](empty_guard=True)
    regex = RegexStage[LEINotation](
        pattern=_LEI_PATTERN, notation_fn=_lei_notation, flags=re.IGNORECASE
    )


# Scaffolder seam: capability.py imports LEIRecognition; keep it an alias.
LEIRecognition = LEIRecognitionGrammar
