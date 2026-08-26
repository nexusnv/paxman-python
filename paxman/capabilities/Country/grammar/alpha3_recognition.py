"""Alpha-3 country code recognition grammar (staged pipeline).

Recognizes exactly 3 ASCII letters as an alpha-3 country code shape. The word
boundary is supplied by BoundaryGuard.word_only() (ADR-0009 §10) so no
hard-coded lookaround literal remains in this file. Syntax only: the grammar
never resolves the code to a country.
"""

from __future__ import annotations

import re

from paxman.capabilities.Country.notation import CountryNotation
from paxman.core.grammar import BoundaryGuard, PipelineGrammar, RegexStage, StandardPre

_GUARD = BoundaryGuard.word_only()
_ALPHA3_PATTERN = _GUARD.lookbehind + r"[A-Za-z]{3}" + _GUARD.lookahead


def _alpha3_notation(match: re.Match[str]) -> CountryNotation:
    """Map an alpha-3 match to its upper-cased notation."""
    return CountryNotation(shape="alpha3", value=match.group(0).upper())


class Alpha3Grammar(PipelineGrammar[CountryNotation]):
    """Recognizes exactly 3 ASCII letters as alpha-3 country code shape.

    Examples: "USA", "GBR", "usa", "gbr"
    Non-examples: "US" (2 letters), "123" (digits), "United" (6 letters)
    """

    name = "alpha3_recognition"
    semantics = "alpha3_recognition"
    single_value = True

    pre = StandardPre[CountryNotation](empty_guard=True)
    regex = RegexStage[CountryNotation](
        pattern=_ALPHA3_PATTERN, notation_fn=_alpha3_notation
    )
