"""Alpha-3 country code recognition grammar (kernel RegexMatcher).

Recognizes exactly 3 ASCII letters as an alpha-3 country code shape.
BoundarySpec.WORD provides word-boundary discipline (ADR-0009 §10).
Syntax only: never resolves the code to a country.
Suppressible short-code matcher (ADR-0009 §16).
"""

from __future__ import annotations

from paxman.capabilities.Country.notation import CountryNotation
from paxman.core.grammar import AnchorSet, BoundarySpec, PipelineGrammar, StandardPre
from paxman.core.grammar.matchers.regex import RegexMatcher
from paxman.core.grammar.scan_context import ScanContext


def _emit(span: tuple[int, int], ctx: ScanContext) -> CountryNotation:
    s, e = span
    raw = ctx.text[s:e]
    return CountryNotation(shape="alpha3", value=raw.upper())


_MATCHER = RegexMatcher(
    pattern=r"[A-Za-z]{3}",
    boundary=BoundarySpec.WORD,
    view=None,
    anchors=AnchorSet(),
    emit=_emit,
    suppressible=True,
)


class Alpha3Grammar(PipelineGrammar[CountryNotation]):
    """Recognizes exactly 3 ASCII letters as alpha-3 country code shape.

    Examples: "USA", "GBR", "usa", "gbr"
    Non-examples: "US" (2 letters), "123" (digits), "United" (6 letters)
    """

    name = "alpha3_recognition"
    semantics = "alpha3_recognition"
    single_value = True

    pre = StandardPre[CountryNotation](empty_guard=True)
    matchers = (_MATCHER,)
