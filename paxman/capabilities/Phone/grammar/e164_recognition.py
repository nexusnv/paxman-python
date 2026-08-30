"""E.164 international number recognition grammar (ScannerMatcher).

Recognizes a leading "+" followed by digits with optional separators
(space, dash, dot, parens). The grammar is intentionally loose — validation
happens in rules. The negative lookbehind (via BoundarySpec.E164_LEFT)
excludes word characters, ":" and "." so email plus-tags, algebra, decimals,
and "tel:+..." are NOT double-matched. The trailing digit-ending guard
forces the match to end on a digit so trailing separators/whitespace/
punctuation are not swallowed. The 15-digit E.164 window is a
separator-skipping bounded window with ``max_window`` as data (ADR-0009
§9.3); the span fixup ``end = start + len(trimmed)`` is preserved exactly
so a following number is not merged into the span.
"""

from __future__ import annotations

import re

from paxman.capabilities.Phone.grammar._common import strip_separators
from paxman.capabilities.Phone.notation import PhoneNotation
from paxman.core.grammar import BoundarySpec, ScannerMatcher, StandardPre
from paxman.core.grammar.pipeline import PipelineGrammar
from paxman.core.grammar.scan_context import ScanContext, View

# Maximum E.164 number length in digits (spec limit; the grammar trims
# runaway matches at this boundary). Duplicated from the rule module on
# purpose: the semantic-purity gate forbids grammar -> rules imports, so
# each side keeps its own copy. Keep in sync with
# rules/e164_ed2010.py:_MAX_E164_DIGITS.
_MAX_E164_DIGITS = 15

# Char window carrying the 15-digit bound as data; separators inflate raw
# length beyond the digit count, so the char window must hold a full
# 15-digit number with separators and the leading "+". Worst case:
# 15 digits + 14 gaps ×3 (" - " space-dash-space) + "+" = 58 chars,
# e.g. "+1 - 2 - 3 - 4 - 5 - 6 - 7 - 8 - 9 - 0 - 1 - 2 - 3 - 4 - 5".
# 64 safely covers that plus the runaway-trim case
# "+15551234567 5551234567" (23 chars) and the oversized first-run case
# "+12345678901234567890" (21 chars) while still bounding the scanner.
# See #65.
_E164_MAX_WINDOW = 64


def _trim_to_e164_boundary(raw: str) -> str:
    """Trim a runaway raw match at the last digit-run group within the limit.

    ``_e164_scan``'s greedy character class consumes separators AND
    following digit runs, so "+15551234567 5551234567" is captured as one raw
    span. The raw match is trimmed back to the last complete digit-run group
    whose inclusion keeps the total digit count at or below
    ``_MAX_E164_DIGITS`` (15), so a legitimate following number is not
    swallowed into the match. If the first run alone exceeds the limit, the
    raw match is kept whole: validation then rejects the oversized value
    instead of silently recognizing a truncated 15-digit prefix.
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


def _e164_scan(view: View, pos: int) -> tuple[int, PhoneNotation] | None:
    """Scanner function: (view, pos) -> (end, Notation) | None.

    Separator-skipping bounded window (ADR-0009 §9.3): at ``pos`` expects a
    leading "+" followed by a digit, then greedily consumes digits and
    separators ``[\\d\\s().\\-]`` ending on a digit, then applies the
    15-digit run-aware trim (``end = start + len(trimmed)``).
    """
    subj = view.subject
    n = len(subj)
    if pos < 0 or pos >= n:
        return None
    if subj[pos] != "+":
        return None
    if pos + 1 >= n or not subj[pos + 1].isdigit():
        return None
    j = pos + 2
    while j < n and (subj[j].isdigit() or subj[j] in "().-" or subj[j].isspace()):
        j += 1
    while j > pos and not subj[j - 1].isdigit():
        j -= 1
    if j <= pos + 1:
        return None
    raw = subj[pos:j]
    trimmed = _trim_to_e164_boundary(raw)
    trimmed_end = pos + len(trimmed)
    return (
        trimmed_end,
        PhoneNotation(shape="e164", value=strip_separators(trimmed, plus=True)),
    )


def _e164_emit(span: tuple[int, int], ctx: ScanContext) -> PhoneNotation:
    s, e = span
    raw = ctx.text[s:e]
    return PhoneNotation(shape="e164", value=strip_separators(raw, plus=True))


_E164_SCANNER = ScannerMatcher(
    scan=_e164_scan,
    boundary=BoundarySpec.E164_LEFT,
    emit=_e164_emit,
    max_window=_E164_MAX_WINDOW,
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
    matchers = (_E164_SCANNER,)
