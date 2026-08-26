"""Alpha-2 country code recognition grammar (staged pipeline).

Recognizes exactly 2 ASCII letters as an alpha-2 country code shape. The word
boundary is supplied by BoundaryGuard.word_only() (ADR-0009 §10) so no
hard-coded lookaround literal remains in this file. Syntax only: the grammar
never resolves the code to a country.
"""

from __future__ import annotations

import re

from paxman.capabilities.Country.notation import CountryNotation
from paxman.core.grammar import BoundaryGuard, PipelineGrammar, RegexStage, StandardPre

_GUARD = BoundaryGuard.word_only()
_ALPHA2_PATTERN = _GUARD.lookbehind + r"[A-Za-z]{2}" + _GUARD.lookahead


def _alpha2_notation(match: re.Match[str]) -> CountryNotation:
    """Map an alpha-2 match to its upper-cased notation."""
    return CountryNotation(shape="alpha2", value=match.group(0).upper())


class Alpha2Grammar(PipelineGrammar[CountryNotation]):
    """Recognizes exactly 2 ASCII letters as alpha-2 country code shape.

    Examples: "US", "GB", "us", "gB"
    Non-examples: "USA" (3 letters), "12" (digits), "U" (1 letter)
    """

    name = "alpha2_recognition"
    semantics = "alpha2_recognition"
    single_value = True

    pre = StandardPre[CountryNotation](empty_guard=True)
    regex = RegexStage[CountryNotation](
        pattern=_ALPHA2_PATTERN, notation_fn=_alpha2_notation
    )
