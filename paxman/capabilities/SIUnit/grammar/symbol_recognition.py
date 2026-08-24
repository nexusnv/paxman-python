"""Symbol recognition grammar for SI Unit (lexicon trie).

Recognizes unit symbols exactly as written (case-exact): base symbols
("m", "kg"), derived special-name symbols ("Pa", "°C"), non-SI symbols
("min", "L"), prefix symbols ("k", "M") and prefixed units ("km", "MHz").
Each recognition emits a span-bearing RecognitionMatch over the symbol
text. Recognition only: no validation, no canonicalization (D1/D2/D6).

Migrated from RegexStage with BoundaryGuard.degree_word_sign to a
lexicon trie (size-gated auto) on the original view. The split-prefix
shape ("k g" -> ``split_symbol_prefix``) is emitted via the token's
first-word check, byte-identically to the legacy ``recognize()``.
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
from paxman.core.grammar.matchers.lexicon import LexiconMatcher
from paxman.core.grammar.scan_context import ScanContext

DUAL_ROLE_PREFIX_SYMBOLS = frozenset({"a", "d", "h", "m"})
PREFIX_ONLY_SYMBOLS = frozenset(PREFIX_SYMBOL_TOKENS) - DUAL_ROLE_PREFIX_SYMBOLS

_BASE_SYMBOL_TOKENS: frozenset[str] = frozenset(SYMBOL_TOKENS)
_SPACED_SYMBOL_TOKENS: frozenset[str] = frozenset(
    f"{p} {s}" for p in PREFIX_ONLY_SYMBOLS for s in SYMBOL_TOKENS
)
_ALL_SYMBOL_TOKENS: frozenset[str] = _BASE_SYMBOL_TOKENS | _SPACED_SYMBOL_TOKENS


def _emit_symbol(span: tuple[int, int], ctx: ScanContext) -> SIUnitNotation:
    s, e = span
    token = ctx.text[s:e]
    parts = token.split()
    if len(parts) >= 2 and parts[0] in PREFIX_ONLY_SYMBOLS:
        shape = "split_symbol_prefix"
    else:
        shape = "symbol"
    return SIUnitNotation(text=token, shape=shape)


_SYMBOL_MATCHER = LexiconMatcher(
    tokens=_ALL_SYMBOL_TOKENS,
    boundary=BoundarySpec.DEGREE_WORD_SIGN,
    view=None,
    anchors=AnchorSet(),
    emit=_emit_symbol,
    representation="auto",
)


class SymbolRecognition(PipelineGrammar[SIUnitNotation]):
    """Grammar: symbol_recognition — case-exact unit symbol tokens."""

    name = "symbol_recognition"
    semantics = "symbol_recognition"

    pre = StandardPre[SIUnitNotation](empty_guard=True)
    matchers = (_SYMBOL_MATCHER,)

    def recognize(self, text: str) -> list[RecognitionMatch[SIUnitNotation]]:
        if not text.strip():
            return []
        ctx = ScanContext.of(text)
        view = ctx.view("__orig__", lambda t: (t, None))
        spans = _SYMBOL_MATCHER.match(view)
        out: list[RecognitionMatch[SIUnitNotation]] = []
        for s, e in spans:
            o_s, o_e = view.original_span(s, e)
            raw = text[o_s:o_e]
            parts = raw.split()
            if len(parts) >= 2 and parts[0] in PREFIX_ONLY_SYMBOLS:
                shape = "split_symbol_prefix"
            else:
                shape = "symbol"
            out.append(
                RecognitionMatch(
                    notation=SIUnitNotation(text=raw, shape=shape),
                    start=o_s,
                    end=o_e,
                    raw_text=raw,
                )
            )
        return out
