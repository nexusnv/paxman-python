"""Numeric (M49) country code recognition grammar (kernel RegexMatcher).

Recognizes 1-3 digits as a numeric country code shape.
BoundarySpec.WORD provides word-boundary discipline (ADR-0009 §10).
Syntax only: never resolves the code to a country.
Suppressible marker present (ADR-0009 §16) — digit hits never collide
with COMMON_WORDS but declaration keeps the short-code surface uniform.
"""

from __future__ import annotations

from paxman.capabilities.Country.notation import CountryNotation
from paxman.core.grammar import AnchorSet, BoundarySpec, PipelineGrammar, StandardPre
from paxman.core.grammar.matchers.regex import RegexMatcher
from paxman.core.grammar.scan_context import ScanContext


def _emit(span: tuple[int, int], ctx: ScanContext) -> CountryNotation:
    s, e = span
    raw = ctx.text[s:e]
    return CountryNotation(shape="numeric", value=raw)


_MATCHER = RegexMatcher(
    pattern=r"\d{1,3}",
    boundary=BoundarySpec.WORD,
    view=None,
    anchors=AnchorSet(),
    emit=_emit,
    suppressible=True,
)


class NumericGrammar(PipelineGrammar[CountryNotation]):
    """Recognizes 1-3 digits as numeric country code shape.

    Examples: "840", "4", "004"
    Non-examples: "US" (letters), "1234" (4 digits), "12a" (alphanumeric)
    """

    name = "numeric_recognition"
    semantics = "numeric_recognition"
    single_value = True

    pre = StandardPre[CountryNotation](empty_guard=True)
    matchers = (_MATCHER,)
