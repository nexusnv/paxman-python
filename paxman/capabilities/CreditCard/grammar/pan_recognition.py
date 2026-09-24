r"""PAN recognition — 12-19 digits, space/hyphen grouped, optional label.

Kernel ScannerMatcher with the four-guard set: word guards (in-pattern
lookarounds + BoundarySpec.WORD), trailing date guard, joined-run orphan
guard, and the scan-side left joined-run guard (Python re forbids
variable-width lookbehind). The body/guards use ASCII [0-9] (never
Unicode \d) and ``_pan_emit`` keeps only ASCII digits — the engine
discards the scan payload.
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
# Digit classes are [0-9], never Unicode \d: Python re \d matches every
# Unicode decimal digit, but _pan_emit only keeps ASCII digits, so a \d in
# the body would let a non-ASCII digit be silently dropped and fabricate a
# PAN that was never written (ASCII-only contract, no-fabrication invariant).
_DATE_GUARD = r"(?!\s[0-9]+/)"
_ORPHAN_GUARD = r"(?!(?:[ \t\-]?[0-9]){1,11}(?![0-9/]))"
_PAN_BODY_RE = re.compile(
    BoundaryGuard.word_only().lookbehind
    + "(?:"
    + "|".join(
        rf"(?:[0-9]{_DATE_GUARD}[ \-]?){{{n - 1}}}[0-9]" for n in range(19, 11, -1)
    )
    + ")"
    + BoundaryGuard.word_only().lookahead
    + _ORPHAN_GUARD
)

_SOFT_RUN = frozenset("0123456789 \t-")


def _left_soft_run_digits(subject: str, body_start: int) -> int:
    """Digits in the soft run ending just before ``body_start``, capped at 12.

    The caller only distinguishes 0 / 1-11 / >=12, so once 12 digits are
    counted the exact total is irrelevant. The cap bounds each call to O(12)
    work instead of rescanning the entire preceding run, keeping recognition
    linear on long digit runs (the uncapped walk was O(n^2): 20k digits took
    ~40s through canonicalize()). The guard decision is unchanged — 12 and
    any larger count both fall outside 1..11, so neither blocks the claim.
    """
    count = 0
    i = body_start
    while i > 0 and subject[i - 1] in _SOFT_RUN:
        i -= 1
        if "0" <= subject[i] <= "9":
            count += 1
            if count >= 12:
                break
    return count


def _pan_scan(view: View, pos: int) -> tuple[int, str] | None:
    """Scan for a PAN body with optional label at the given position."""
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
    """Emit PAN notation from the ASCII digits in the span."""
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
