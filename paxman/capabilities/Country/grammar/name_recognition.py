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
from paxman.capabilities.Country.notation import CountryNotation, normalize_name
from paxman.core.domain import RecognitionMatch
from paxman.core.grammar import (
    AnchorSet,
    BoundarySpec,
    PipelineGrammar,
    StandardPre,
)
from paxman.core.grammar.matchers.lexicon import LexiconMatcher
from paxman.core.grammar.normalizers import CountryNameFold
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
    # View offsets are None for AccentStrip (length-preserving), so span
    # maps directly to original text indices. Use original text slice.
    raw = ctx.text[s:e]
    return CountryNotation(shape="name", value=raw)


_LEXICON_MATCHER = LexiconMatcher(
    tokens=_LEXICON_TOKENS,
    boundary=BoundarySpec.WORD,
    view="normalized",
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

    def recognize(self, text: str) -> list[RecognitionMatch[CountryNotation]]:
        if not text.strip():
            return []
        ctx = ScanContext.of(text)
        view = ctx.view("normalized", CountryNameFold().normalize)
        spans = _LEXICON_MATCHER.match(view)
        out: list[RecognitionMatch[CountryNotation]] = []
        for s, e in spans:
            o_s, o_e = view.original_span(s, e)
            raw = text[o_s:o_e]
            out.append(
                RecognitionMatch(
                    notation=CountryNotation(shape="name", value=raw),
                    start=o_s,
                    end=o_e,
                    raw_text=raw,
                )
            )
        # Whole-input spans are a subset of the trie emission when the
        # view correctly normalizes punctuation and separators, but we keep
        # the explicit WholeInputLookup parity check for byte-identical
        # whole-input semantics on edge punctuation cases.
        trimmed = text.strip()
        if normalize_name(trimmed) in _KNOWN_NAME_KEYS:
            start = len(text) - len(text.lstrip())
            end = start + len(trimmed)
            if not any(m.start == start and m.end == end for m in out):
                raw = text[start:end]
                out.append(
                    RecognitionMatch(
                        notation=CountryNotation(shape="name", value=raw),
                        start=start,
                        end=end,
                        raw_text=raw,
                    )
                )
        out.sort(key=lambda m: (m.start, -(m.end - m.start)))
        return out
