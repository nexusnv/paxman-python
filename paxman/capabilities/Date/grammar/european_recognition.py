"""European date recognition — wrapper for consolidated date."""

from __future__ import annotations

from paxman.capabilities.Date.grammar.date_recognition import EUROPEAN_MATCHER
from paxman.capabilities.Date.notation import DateNotation
from paxman.core.grammar import PipelineGrammar, StandardPre


class EuropeanDateGrammar(PipelineGrammar[DateNotation]):
    name = "european_recognition"
    semantics = "european_calendar_date"
    single_value = True

    pre = StandardPre[DateNotation](empty_guard=True)
    matchers = (EUROPEAN_MATCHER,)  # type: ignore[assignment]
