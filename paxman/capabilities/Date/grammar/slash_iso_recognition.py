"""Slash-ISO date recognition — wrapper for consolidated date."""

from __future__ import annotations

from paxman.capabilities.Date.grammar.date_recognition import SLASH_ISO_MATCHER
from paxman.capabilities.Date.notation import DateNotation
from paxman.core.grammar import PipelineGrammar, StandardPre


class SlashISODateGrammar(PipelineGrammar[DateNotation]):
    name = "slash_iso_recognition"
    semantics = "iso8601_calendar_date"
    single_value = True

    pre = StandardPre[DateNotation](empty_guard=True)
    matchers = (SLASH_ISO_MATCHER,)  # type: ignore[assignment]
