"""Slash-ISO date recognition grammar (staged pipeline).

Recognizes YYYY/MM/DD format — the common prose alternative to the strict
ISO dash form. Unlike the strict ``YYYY-MM-DD`` ISO grammar, this grammar
accepts 1-2 digit month/day (``2026/1/5``) and zero-pads via the validating
rule. The digit lookarounds (via BoundaryGuard.digit()) keep the pattern
disjoint from surrounding digits. Notation mapping: N1=year, N2=month, N3=day.
"""

from __future__ import annotations

import re

from paxman.capabilities.Date.notation import DateNotation
from paxman.core.grammar import BoundaryGuard, PipelineGrammar, RegexStage, StandardPre

_GUARD = BoundaryGuard.digit()
_SLASH_ISO_PATTERN = (
    _GUARD.lookbehind + r"(\d{4})/(\d{1,2})/(\d{1,2})" + _GUARD.lookahead
)


def _slash_iso_notation(match: re.Match[str]) -> DateNotation:
    """Map a slash-ISO match to its year/month/day notation."""
    return DateNotation(N1=match.group(1), N2=match.group(2), N3=match.group(3))


class SlashISODateGrammar(PipelineGrammar[DateNotation]):
    """Slash-delimited ISO date recognition: YYYY/MM/DD (lenient).

    Shares the ISO 8601 position mapping (N1=year, N2=month, N3=day) with a
    ``/`` delimiter instead of ``-``; unlike the strict ``YYYY-MM-DD`` grammar,
    single-digit month/day components are accepted and zero-padded by the
    validating rule (``2026/1/5`` → ``2026-01-05``). The leading 4-digit year
    keeps the pattern disjoint from the US and European grammars, which both
    require a leading month/day. Digit lookarounds keep the match disjoint
    from surrounding digits, mirroring the other shipped date grammars, so a
    longer digit run (e.g. an ID like ``12026/01/15``) is never partially
    matched as a date.

    Strictness note: the strict ISO grammar requires ``MM``/``DD`` exactly
    2-digit; this slash grammar is intentionally lenient (1-2 digit) for prose.

    Notation mapping: N1=year, N2=month, N3=day
    """

    name = "slash_iso_recognition"
    semantics = "iso8601_calendar_date"
    single_value = True

    pre = StandardPre[DateNotation](empty_guard=True)
    regex = RegexStage[DateNotation](
        pattern=_SLASH_ISO_PATTERN, notation_fn=_slash_iso_notation
    )
