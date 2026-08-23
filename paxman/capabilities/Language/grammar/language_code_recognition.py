"""Language code recognition — bare 2-3|5-8 via BoundaryGuard.word_sign."""

from __future__ import annotations

import re

from paxman.capabilities.Language.notation import LanguageNotation
from paxman.core.grammar import BoundaryGuard, PipelineGrammar, RegexStage, StandardPre

_GUARD = BoundaryGuard.word_sign()
_CODE_PATTERN = (
    _GUARD.lookbehind + r"(?P<code>[A-Za-z]{2,3}|[A-Za-z]{5,8})" + _GUARD.lookahead
)


def _code_notation(match: re.Match[str]) -> LanguageNotation:
    code = match.group("code")
    lower = code.lower()
    return LanguageNotation(
        language=lower,
        extlang="",
        script="",
        region="",
        variant="",
        extension="",
        privateuse="",
        grandfathered="",
        compact=lower,
        raw_value=lower,
    )


class LanguageCodeGrammar(PipelineGrammar[LanguageNotation]):
    """Bare language code recognition — 2-3 or 5-8 letters."""

    name = "language_code_recognition"
    semantics = "language_code"
    single_value = True

    pre = StandardPre[LanguageNotation](empty_guard=True)
    regex = RegexStage[LanguageNotation](
        pattern=_CODE_PATTERN,
        notation_fn=_code_notation,
    )
