"""CLDR currency symbol recognition grammar (staged pipeline).

Recognizes a standalone currency symbol token (qualified or bare) as one
span-bearing token. The alternation is built from SYMBOL_TOKENS
(qualified-first, longest-first — D4) and guarded by word_sign boundaries;
the grammar emits the verbatim token with shape "symbol" or
"qualified_symbol". Syntax only: resolving the symbol to a code is the
rules' job.
"""

from __future__ import annotations

from paxman.capabilities.Currency.grammar.data.currency_symbols import SYMBOL_TOKENS
from paxman.capabilities.Currency.notation import CurrencyNotation
from paxman.core.grammar import (
    BoundaryGuard,
    LexiconStage,
    PipelineGrammar,
    StandardPre,
)


def _is_qualified(token: str) -> bool:
    """Whether a symbol token carries an ASCII letter (e.g. "US$")."""
    return any(char.isascii() and char.isalpha() for char in token)


def _symbol_notation(token: str) -> CurrencyNotation:
    """Map a matched symbol token to its qualified/bare notation."""
    return CurrencyNotation(
        text=token,
        shape="qualified_symbol" if _is_qualified(token) else "symbol",
    )


class SymbolRecognition(PipelineGrammar[CurrencyNotation]):
    """Recognizes standalone CLDR currency symbol tokens.

    A token is "qualified" when it embeds an ASCII letter ("US$", "A$",
    "R$") and "bare" otherwise ("$", "€", "¥"). Symbols are case-exact —
    no case folding (symbols are arbitrary glyph strings), so "US$" matches
    but "us$" is MISSING (word grammar and code grammar are case-insensitive
    by contrast: "usd"→"USD", "euro"→"euro"). The lexicon is guarded by
    word_sign lookarounds so amount-glued ("US$5", "$500") and inside-token
    ("x€") forms are rejected. Shared bare symbols ("$", "¥", "£") require
    the contract's default_currency opt-in to resolve; definitive symbols
    ("€"→"EUR") and qualified symbols ("US$"→"USD") ignore it.

    Examples: "US$" -> text "US$", shape "qualified_symbol"
              "€"    -> text "€",    shape "symbol"
    Non-examples: "us$" (lowercase qualified, MISSING), "Lei" (capitalized
        "lei"→"RON" is case-exact, so "Lei" is INVALID via code path).
    """

    name = "symbol_recognition"
    semantics = "symbol_recognition"
    single_value = True

    pre = StandardPre[CurrencyNotation](empty_guard=True)
    lexicon = LexiconStage(
        tokens=SYMBOL_TOKENS,
        boundary=BoundaryGuard.word_sign(),
        longest_first=True,
        notation_fn=_symbol_notation,
    )
