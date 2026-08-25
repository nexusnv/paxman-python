"""US date recognition grammar (staged pipeline).

Recognizes MM/DD/YYYY and MM/DD/YY formats. The 4-digit and 2-digit year
variants are merged into one year-length alternation; the digit lookarounds
(via BoundaryGuard.digit()) keep the pattern disjoint from surrounding
digits. Notation mapping: N1=month, N2=day, N3=year.

This grammar shares an identical regex shape with ``EuropeanDateGrammar``
(``\\d{1,2}/\\d{1,2}/(\\d{4}|\\d{2})``) — the same raw ``MM/DD`` span is
recognized by both grammars with different ``semantics`` (``us_calendar_date``
vs ``european_calendar_date``). The two notations carry identical ``N1,N2,N3``
values for the same raw text; the validating rules then interpret them under
different specs (month-first vs day-first), producing the cross-grammar
doubling noted in the audit (ambiguous ``01/02/2026`` → 4 candidates, 2 values).
Lenient 1-2 digit month/day; strict validation is rule-owned.

Note: The legacy bespoke ``recognize()`` ran two separate ``finditer`` loops
(4-digit year first, then 2-digit), so grouped matches by year length rather
than document order (e.g. ``"01/02/26 foo 01/02/2026"`` yielded
``[01/02/2026, 01/02/26]``). The staged ``(\\d{4}|\\d{2})`` alternation uses a
single ``finditer`` in document order (``[01/02/26, 01/02/2026]``). The engine
(``paxman/engine/orchestrator.py``) sorts by ``start`` before dedup, so
end-to-end ``canonicalize()`` results are identical; direct ``recognize()``
order is now document-order. See ADR-0008 D1 and harness note in
``tests/property/test_grammar_stage_parity.py``.
"""

from __future__ import annotations

import re

from paxman.capabilities.Date.notation import DateNotation
from paxman.core.grammar import BoundaryGuard, PipelineGrammar, RegexStage, StandardPre

_GUARD = BoundaryGuard.digit()
_US_PATTERN = (
    _GUARD.lookbehind + r"(\d{1,2})/(\d{1,2})/(\d{4}|\d{2})" + _GUARD.lookahead
)


def _us_notation(match: re.Match[str]) -> DateNotation:
    """Map a US date match to its month/day/year notation."""
    return DateNotation(N1=match.group(1), N2=match.group(2), N3=match.group(3))


class USDateGrammar(PipelineGrammar[DateNotation]):
    """US date recognition: MM/DD/YYYY and MM/DD/YY (lenient).

    Both year-length variants carry digit lookarounds, so a date glued to
    surrounding digits (e.g. an ID like ``1201/02/2026``) is never partially
    matched. Lenient 1-2 digit month/day; ``7/26/2026`` and ``07/26/26`` both
    match and are validated via ``two_digit_base_year`` expansion.

    Shares the identical ``\\d{1,2}/\\d{1,2}/`` shape with the European grammar;
    cross-grammar doubling is intentional (audit B3).

    Notation mapping: N1=month, N2=day, N3=year
    """

    name = "us_recognition"
    semantics = "us_calendar_date"
    single_value = True

    pre = StandardPre[DateNotation](empty_guard=True)
    regex = RegexStage[DateNotation](pattern=_US_PATTERN, notation_fn=_us_notation)
