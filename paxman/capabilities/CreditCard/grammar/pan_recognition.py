"""PAN recognition — 12-19 digits, space/hyphen grouped, optional label.

Kernel ScannerMatcher with the four-guard set: word guards (in-pattern
lookarounds + BoundarySpec.WORD), trailing date guard, joined-run orphan
guard, and the scan-side left joined-run guard (Python re forbids
variable-width lookbehind). ASCII-digit filtering lives only in
``_pan_scan``/``_pan_emit`` — the engine discards the scan payload.
"""

from __future__ import annotations

import re

from paxman.capabilities.CreditCard.notation import PANNotation
from paxman.core.grammar import BoundarySpec, ScannerMatcher
from paxman.core.grammar.boundary import BoundaryGuard
from paxman.core.grammar.pipeline import PipelineGrammar
from paxman.core.grammar.scan_context import ScanContext, View

# Label branch: human field labels only (card number / pan / cc / credit
# card), matched at scan time with a mandatory one-or-more separator — never
# zero-width (glued "PAN4111111111111111" stays MISSING, ISIN/IBAN/BIC
# precedent). Label separators are space/hyphen/colon; the BODY tolerates a
# single [ \-] per gap only (validator.js / braintree evidence); dots/
# underscores/slashes are NOT tolerated in v1 (DEFER).
_PAN_LABEL_RE = re.compile(
    r"(?:(?ai:credit[\s-]?card(?:[\s-]?number)?|card[\s-]?number|pan|cc))[\s:-]+"
)

# Body: longest-first 19->12 alternation + guards, compiled once at module
# scope (never inside scan). Two tail guards:
#   _DATE_GUARD    — a branch may not end by absorbing the " 12" of
#                    " 12/27" (fires only when a space+digits group would
#                    terminate at "/", so 4-4-4-4 grouping, expiry words,
#                    and mention pairs are untouched);
#   _ORPHAN_GUARD  — a claim may not end with a 1-11-digit continuation in
#                    the same space/tab/hyphen run (a sub-floor fragment);
#                    a >=12 continuation is a separate mention and is left
#                    for the next scan position (two matches).
_DATE_GUARD = r"(?!\s\d+/)"
_ORPHAN_GUARD = r"(?!(?:[ \t\-]?\d){1,11}(?![0-9/]))"
_PAN_BODY_RE = re.compile(
    BoundaryGuard.word_only().lookbehind
    + "(?:"
    + "|".join(rf"(?:\d{_DATE_GUARD}[ \-]?){{{n - 1}}}\d" for n in range(19, 11, -1))
    + ")"
    + BoundaryGuard.word_only().lookahead
    + _ORPHAN_GUARD
)

_SOFT_RUN = frozenset("0123456789 \t-")


def _left_soft_run_digits(subject: str, body_start: int) -> int:
    """Digits in the space/tab/hyphen run ending just before ``body_start``."""
    i = body_start
    while i > 0 and subject[i - 1] in _SOFT_RUN:
        i -= 1
    return sum(1 for ch in subject[i:body_start] if "0" <= ch <= "9")


def _pan_scan(view: View, pos: int) -> tuple[int, str] | None:
    subject = view.subject
    label = _PAN_LABEL_RE.match(subject, pos)
    if label is not None:
        body_start = label.end()
    else:
        body_start = pos
        if not ("0" <= subject[pos] <= "9"):
            return None
    # Left joined-run guard: 1-11 soft-joined digits before the claim start
    # mean a longer run that must be judged from its own origin — never
    # carved from inside (double-space/tab inner starts, 20-run inner
    # starts). Python, because Python re has no variable-width lookbehind
    # (an in-pattern guard would need every fragment length 1-11 x every
    # gap shape enumerated as fixed-width lookbehind clauses).
    frag = _left_soft_run_digits(subject, body_start)
    if 1 <= frag <= 11:
        return None
    m = _PAN_BODY_RE.match(subject, body_start)
    if m is None:
        return None
    # Span starts at pos (label included when matched). The engine discards
    # this payload (scanner.match: end, _notation = res) and rebuilds
    # notation in _pan_emit — emit owns the digits filter.
    return (m.end(), m.group(0))


def _pan_emit(span: tuple[int, int], ctx: ScanContext) -> PANNotation:
    s, e = span
    digits = "".join(ch for ch in ctx.text[s:e] if "0" <= ch <= "9")
    return PANNotation(digits=digits, compact=digits)


_PAN_SCANNER = ScannerMatcher(
    scan=_pan_scan,
    boundary=BoundarySpec.WORD,
    emit=_pan_emit,
)


class PANRecognitionGrammar(PipelineGrammar[PANNotation]):
    """PAN recognition — 12-19 digits, space/hyphen grouped, optional label."""

    name = "pan_recognition"
    semantics = "pan_recognition"
    single_value = True
    matchers = (_PAN_SCANNER,)
