"""Alpha-2 country code recognition grammar (kernel RegexMatcher).

Recognizes exactly 2 ASCII letters as an alpha-2 country code shape.
BoundarySpec.WORD provides word-boundary discipline (ADR-0009 §10).
Syntax only: never resolves the code to a country.
Suppressible short-code matcher (ADR-0009 §16): with
suppress_common_words=True the high-frequency word hits are skipped in
the engine loop (provenance-neutral, default off).
"""

from __future__ import annotations

from paxman.capabilities.Country.notation import CountryNotation
from paxman.core.grammar import AnchorSet, BoundarySpec, PipelineGrammar, StandardPre
from paxman.core.grammar.matchers.regex import RegexMatcher
from paxman.core.grammar.scan_context import ScanContext


def _emit(span: tuple[int, int], ctx: ScanContext) -> CountryNotation:
    s, e = span
    raw = ctx.text[s:e]
    return CountryNotation(shape="alpha2", value=raw.upper())


_MATCHER = RegexMatcher(
    pattern=r"[A-Za-z]{2}",
    boundary=BoundarySpec.WORD,
    view=None,
    anchors=AnchorSet(),
    emit=_emit,
    suppressible=True,
)


class Alpha2Grammar(PipelineGrammar[CountryNotation]):
    """Recognizes exactly 2 ASCII letters as alpha-2 country code shape.

    Examples: "US", "GB", "us", "gB"
    Non-examples: "USA" (3 letters), "12" (digits), "U" (1 letter)
    """

    name = "alpha2_recognition"
    semantics = "alpha2_recognition"
    single_value = True

    pre = StandardPre[CountryNotation](empty_guard=True)
    matchers = (_MATCHER,)
