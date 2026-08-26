"""E.164 international number recognition grammar (staged pipeline).

Recognizes a leading "+" followed by digits with optional separators
(space, dash, dot, parens). The grammar is intentionally loose — validation
happens in rules. The negative lookbehind (via BoundaryGuard.e164()) excludes
word characters, ":", and "." so email plus-tags, algebra, decimals, and
"tel:+..." are NOT double-matched. The trailing digit-ending lookbehind
forces the match to end on a digit so trailing separators/whitespace/
punctuation are not swallowed. A PostStage trims runaway matches at the
15-digit E.164 window (ADR-0008 S5) so a following number is not merged into
the span.
"""

from __future__ import annotations

import functools
import re

from paxman.capabilities.Phone.grammar._common import strip_separators
from paxman.capabilities.Phone.notation import PhoneNotation
from paxman.core.domain import RecognitionMatch
from paxman.core.grammar import (
    BoundaryGuard,
    PipelineGrammar,
    PostStage,
    RegexStage,
    StandardPre,
)

# Maximum E.164 number length in digits (spec limit; the grammar trims
# runaway matches at this boundary). Duplicated from the rule module on
# purpose: the semantic-purity gate forbids grammar -> rules imports, so
# each side keeps its own copy. Keep in sync with
# rules/e164_ed2010.py:_MAX_E164_DIGITS.
_MAX_E164_DIGITS = 15


@functools.lru_cache(maxsize=256)
def _trim_to_e164_boundary(raw: str) -> str:
    """Trim a runaway raw match at the last digit-run group within the limit.

    ``_E164_PATTERN``'s trailing character class consumes separators AND
    following digit runs, so "+15551234567 5551234567" is captured as one raw
    span. The raw match is trimmed back to the last complete digit-run group
    whose inclusion keeps the total digit count at or below
    ``_MAX_E164_DIGITS`` (15), so a legitimate following number is not
    swallowed into the match. If the first run alone exceeds the limit, the
    raw match is kept whole: validation then rejects the oversized value
    instead of silently recognizing a truncated 15-digit prefix.

    Cached so the paired ``_e164_notation`` / ``_e164_trim`` calls for the
    same match reuse a single trimmed result instead of scanning digit runs
    twice.
    """
    runs = list(re.finditer(r"\d+", raw))
    total = 0
    for index, run in enumerate(runs):
        total += len(run.group(0))
        if total > _MAX_E164_DIGITS:
            if index == 0:
                return raw
            return raw[: runs[index - 1].end()]
    return raw


# Body: "+" then digits with optional separators, ending on a digit. The
# leading lookbehind is supplied by BoundaryGuard.e164() (ADR-0009 §10) so no
# hard-coded lookaround literal remains in this file.
_E164_BODY = r"\+\d[\d\s().\-]*(?<=\d)"
_GUARD = BoundaryGuard.e164()
_E164_PATTERN = _GUARD.lookbehind + _E164_BODY


def _e164_notation(match: re.Match[str]) -> PhoneNotation:
    """Map a raw E.164 match to its digit-only notation (trimmed to 15 digits)."""
    raw = _trim_to_e164_boundary(match.group(0))
    return PhoneNotation(shape="e164", value=strip_separators(raw, plus=True))


def _e164_trim(
    match: RecognitionMatch[PhoneNotation],
) -> RecognitionMatch[PhoneNotation]:
    """Adjust the span to the trimmed 15-digit window (end = start + len)."""
    raw = _trim_to_e164_boundary(match.raw_text)
    return RecognitionMatch(
        notation=match.notation,
        start=match.start,
        end=match.start + len(raw),
        raw_text=raw,
    )


class E164Grammar(PipelineGrammar[PhoneNotation]):
    """Recognizes E.164-style international numbers (leading +).

    Examples: "+15551234567", "+1 555 123 4567", "+44-20-7946-0958"
    Non-examples: "15551234567" (no +), "(555) 123-4567" (national format)
    """

    name = "e164_recognition"
    semantics = "e164_international"
    single_value = True

    pre = StandardPre[PhoneNotation](empty_guard=True)
    regex = RegexStage[PhoneNotation](pattern=_E164_PATTERN, notation_fn=_e164_notation)
    post = PostStage[PhoneNotation](transform=_e164_trim)
