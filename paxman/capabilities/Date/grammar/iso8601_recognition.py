"""ISO 8601 date recognition grammar (staged pipeline).

Recognizes strict YYYY-MM-DD extended format (ISO 8601-1:2019 §4.3.1).
Requires 4-digit year and 2-digit month/day with dash delimiter; single-digit
month/day (``2026-1-5``) is not recognized and is ``MISSING`` — use the
slash variants for lenient 1-2 digit handling. The digit lookarounds are
supplied by BoundaryGuard.digit() (ADR-0008 D5) so no hard-coded lookaround
literal remains. Notation mapping: N1=year, N2=month, N3=day.
"""

from __future__ import annotations

import re

from paxman.capabilities.Date.notation import DateNotation
from paxman.core.grammar import BoundaryGuard, PipelineGrammar, RegexStage, StandardPre

_GUARD = BoundaryGuard.digit()
_ISO8601_PATTERN = _GUARD.lookbehind + r"(\d{4})-(\d{2})-(\d{2})" + _GUARD.lookahead


def _iso_notation(match: re.Match[str]) -> DateNotation:
    """Map an ISO 8601 match to its year/month/day notation."""
    return DateNotation(N1=match.group(1), N2=match.group(2), N3=match.group(3))


class ISO8601DateGrammar(PipelineGrammar[DateNotation]):
    """ISO 8601 date recognition: strict YYYY-MM-DD (extended format).

    Strict fixed-width: ``YYYY-MM-DD`` with ``YYYY`` 4-digit and ``MM``/``DD``
    exactly 2-digit, dash-delimited, per ISO 8601-1:2019 §4.3.1. Single-digit
    components (``2026-1-5``) are not recognized here — they are ``MISSING``;
    slash grammars handle lenient 1-2 digit month/day with zero-padding.

    Digit lookarounds keep the pattern disjoint from surrounding digits, so a
    longer digit run (e.g. an ID like ``12026-01-15``) is never partially
    matched as a date, mirroring the other shipped date grammars.

    Notation mapping: N1=year, N2=month, N3=day
    """

    name = "iso8601_recognition"
    semantics = "iso8601_calendar_date"
    single_value = True

    pre = StandardPre[DateNotation](empty_guard=True)
    regex = RegexStage[DateNotation](
        pattern=_ISO8601_PATTERN, notation_fn=_iso_notation
    )
