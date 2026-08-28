"""ISO 8601 date recognition — thin wrapper delegating to consolidated date_recognition.

Kept for import compatibility; capability now uses DateGrammar (4 candidates).
"""

from __future__ import annotations

from typing import Any, ClassVar

from paxman.capabilities.Date.grammar.date_recognition import ISO_MATCHER
from paxman.capabilities.Date.notation import DateNotation
from paxman.core.grammar import PipelineGrammar, StandardPre


class ISO8601DateGrammar(PipelineGrammar[DateNotation]):
    """Wrapper: iso8601 candidate only."""

    name = "iso8601_recognition"
    semantics = "iso8601_calendar_date"
    single_value = True

    pre = StandardPre[DateNotation](empty_guard=True)
    matchers: ClassVar[tuple[Any, ...] | None] = (ISO_MATCHER,)
