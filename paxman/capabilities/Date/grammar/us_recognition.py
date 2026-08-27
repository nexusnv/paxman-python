"""US date recognition — thin wrapper delegating to consolidated date_recognition."""

from __future__ import annotations

from paxman.capabilities.Date.grammar.date_recognition import US_MATCHER
from paxman.capabilities.Date.notation import DateNotation
from paxman.core.grammar import PipelineGrammar, StandardPre


class USDateGrammar(PipelineGrammar[DateNotation]):
    name = "us_recognition"
    semantics = "us_calendar_date"
    single_value = True

    pre = StandardPre[DateNotation](empty_guard=True)
    matchers = (US_MATCHER,)  # type: ignore[assignment]
