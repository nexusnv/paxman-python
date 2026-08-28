"""Symbol recognition grammar for SI Unit (lexicon trie + combinator).

Recognizes unit symbols exactly as written (case-exact): base symbols
("m", "kg"), derived special-name symbols ("Pa", "°C"), non-SI symbols
("min", "L"), prefix symbols ("k", "M") and prefixed units ("km", "MHz").
Each recognition emits a span-bearing RecognitionMatch over the symbol
text. Recognition only: no validation, no canonicalization (D1/D2/D6).

Split-prefix shape ("k g" -> ``split_symbol_prefix``) is now via a
combinator seq(prefix_lexicon, ws, unit_lexicon) per ADR §9.4 R4,
replacing the materialized product trie (24×820≈19,530 tokens) with a
base lexicon of 930 tokens + combinator. Byte-identical to legacy.
"""

from __future__ import annotations

from paxman.capabilities.SIUnit.grammar.data.prefix_tokens import PREFIX_SYMBOL_TOKENS
from paxman.capabilities.SIUnit.grammar.data.unit_symbol_tokens import SYMBOL_TOKENS
from paxman.capabilities.SIUnit.notation import SIUnitNotation
from paxman.core.domain import RecognitionMatch
from paxman.core.grammar import (
    AnchorSet,
    BoundarySpec,
    PipelineGrammar,
    StandardPre,
)
from paxman.core.grammar.matchers.combinator import CombinatorMatcher
from paxman.core.grammar.matchers.lexicon import LexiconMatcher
from paxman.core.grammar.matchers.regex import RegexMatcher
from paxman.core.grammar.scan_context import ScanContext

DUAL_ROLE_PREFIX_SYMBOLS = frozenset({"a", "d", "h", "m"})
PREFIX_ONLY_SYMBOLS = frozenset(PREFIX_SYMBOL_TOKENS) - DUAL_ROLE_PREFIX_SYMBOLS

_BASE_SYMBOL_TOKENS: frozenset[str] = frozenset(SYMBOL_TOKENS)
_ALL_SYMBOL_TOKENS: frozenset[str] = _BASE_SYMBOL_TOKENS


def _emit_symbol(span: tuple[int, int], ctx: ScanContext) -> SIUnitNotation:
    s, e = span
    token = ctx.text[s:e]
    return SIUnitNotation(text=token, shape="symbol")


def _emit_split(span: tuple[int, int], ctx: ScanContext) -> SIUnitNotation:
    s, e = span
    token = ctx.text[s:e]
    return SIUnitNotation(text=token, shape="split_symbol_prefix")


_BASE_MATCHER = LexiconMatcher(
    tokens=_ALL_SYMBOL_TOKENS,
    boundary=BoundarySpec.DEGREE_WORD_SIGN,
    view=None,
    anchors=AnchorSet(),
    emit=_emit_symbol,
    representation="auto",
)

_PREFIX_LEX = LexiconMatcher(
    tokens=PREFIX_ONLY_SYMBOLS,
    boundary=None,
    view=None,
    anchors=AnchorSet(),
    representation="auto",
)

_WS_MATCHER = RegexMatcher(
    pattern=r"\s+",
    boundary=None,
    view=None,
    anchors=AnchorSet(),
)

_UNIT_LEX = LexiconMatcher(
    tokens=_BASE_SYMBOL_TOKENS,
    boundary=None,
    view=None,
    anchors=AnchorSet(),
    representation="auto",
)

_COMBINATOR_MATCHER = CombinatorMatcher(
    expr=("seq", [_PREFIX_LEX, _WS_MATCHER, _UNIT_LEX]),
    view_name=None,
    boundary=BoundarySpec.DEGREE_WORD_SIGN,
    emit=_emit_split,
)


class SymbolRecognition(PipelineGrammar[SIUnitNotation]):
    """Grammar: symbol_recognition — case-exact unit symbol tokens."""

    # Guard: base lexicon is 930 tokens (historic spec said 820 pre-r/q expansion).
    # Product trie 19,530 removed; combinator provides split shape.
    assert len(_ALL_SYMBOL_TOKENS) == 930, (
        f"base lexicon size drift: {len(_ALL_SYMBOL_TOKENS)} != 930"
    )
    # Keep 820 guard comment for audit (R4): historic 820, now 930.
    # assert len(_ALL_SYMBOL_TOKENS) == 820  # historic

    name = "symbol_recognition"
    semantics = "symbol_recognition"

    pre = StandardPre[SIUnitNotation](empty_guard=True)
    matchers = (_BASE_MATCHER, _COMBINATOR_MATCHER)

    def recognize(self, text: str) -> list[RecognitionMatch[SIUnitNotation]]:
        from paxman.core.grammar.engine_loop import run_matchers

        matches = run_matchers(text, [self])
        # Longer-wins dedup within grammar (mirrors _dedup_spans)
        # Keeps byte-identical parity with legacy product trie.
        ordered = sorted(matches, key=lambda m: (m.start, -(m.end - m.start)))
        kept: list[RecognitionMatch[SIUnitNotation]] = []
        for m in ordered:
            if any(o.start <= m.start and m.end <= o.end for o in kept):
                continue
            kept.append(m)
        kept.sort(key=lambda m: (m.start, m.end))
        return kept
