"""Country name recognition grammar.

Recognizes country name representations from per-locale key sets without
assigning canonical meaning. The input is normalized for membership only;
the trimmed input token is returned as the notation value. Provenance-backed
validation rules own every token-to-country decision.
"""

from __future__ import annotations

from paxman.capabilities.Country.grammar.data.chinese_names import (
    CHINESE_NAME_KEYS,
)
from paxman.capabilities.Country.grammar.data.english_names import (
    ENGLISH_NAME_KEYS,
)
from paxman.capabilities.Country.grammar.data.historical_names import (
    HISTORICAL_NAME_KEYS,
)
from paxman.capabilities.Country.grammar.data.localized_names import (
    LOCALIZED_NAME_KEYS,
)
from paxman.capabilities.Country.notation import CountryNotation
from paxman.core.grammar import (
    AnchorSet,
    BoundarySpec,
    PipelineGrammar,
    StandardPre,
)
from paxman.core.grammar.matchers.lexicon import LexiconMatcher
from paxman.core.grammar.scan_context import ScanContext

# Union of every recognized name representation across locales.
_KNOWN_NAME_KEYS = frozenset(
    ENGLISH_NAME_KEYS | HISTORICAL_NAME_KEYS | CHINESE_NAME_KEYS | LOCALIZED_NAME_KEYS
)

# Lexicon tokens are lowercased for the AccentStrip (normalized) view.
# AccentStrip lowercases and strips accents; the normalized keys are upper
# but case-insensitive, so lowercasing preserves matching on the normalized view.
_LEXICON_TOKENS: frozenset[str] = frozenset(k.lower() for k in _KNOWN_NAME_KEYS)


def _emit(span: tuple[int, int], ctx: ScanContext) -> CountryNotation:
    s, e = span
    raw = ctx.text[s:e]
    return CountryNotation(shape="name", value=raw)


_LEXICON_MATCHER = LexiconMatcher(
    tokens=_LEXICON_TOKENS,
    boundary=BoundarySpec.WORD,
    view="country_normalized",
    anchors=AnchorSet(),
    emit=_emit,
    representation="trie",
)


class NameGrammar(PipelineGrammar[CountryNotation]):
    """Recognizes country name representations from recognition key sets.

    Decides whether an input is a known country name representation and
    returns it unchanged as the notation value. It does not resolve names
    to canonical countries — validation rules assign meaning with
    provenance.

    Examples: "United States" → value="United States"
              "USA" → value="USA"
              "中国" → value="中国"
              "Alemania" → value="Alemania"
              "Burma" → value="Burma"
    Non-examples: "840" → [] (no name match)
                  "" → [] (empty)
                  "XYZ" → [] (unknown name)
    """

    name = "name_recognition"
    semantics = "name_recognition"
    single_value = True

    pre = StandardPre[CountryNotation](empty_guard=True)
    matchers = (_LEXICON_MATCHER,)
