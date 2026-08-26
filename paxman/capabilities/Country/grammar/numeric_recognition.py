"""Numeric (M49) country code recognition grammar (staged pipeline).

Recognizes 1-3 digits as a numeric country code shape. The word boundary is
supplied by BoundaryGuard.word_only() (ADR-0009 §10) so no hard-coded
lookaround literal remains in this file. Syntax only: the grammar never
resolves the code to a country.
"""

from __future__ import annotations

import re

from paxman.capabilities.Country.notation import CountryNotation
from paxman.core.grammar import BoundaryGuard, PipelineGrammar, RegexStage, StandardPre

_GUARD = BoundaryGuard.word_only()
_NUMERIC_PATTERN = _GUARD.lookbehind + r"\d{1,3}" + _GUARD.lookahead


def _numeric_notation(match: re.Match[str]) -> CountryNotation:
    """Map a numeric match to its verbatim notation."""
    return CountryNotation(shape="numeric", value=match.group(0))


class NumericGrammar(PipelineGrammar[CountryNotation]):
    """Recognizes 1-3 digits as numeric country code shape.

    Examples: "840", "4", "004"
    Non-examples: "US" (letters), "1234" (4 digits), "12a" (alphanumeric)
    """

    name = "numeric_recognition"
    semantics = "numeric_recognition"
    single_value = True

    pre = StandardPre[CountryNotation](empty_guard=True)
    regex = RegexStage[CountryNotation](
        pattern=_NUMERIC_PATTERN, notation_fn=_numeric_notation
    )
