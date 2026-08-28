"""ISO 4217 alpha-3 currency code recognition grammar (kernel RegexMatcher).

Recognizes a standalone 3-letter ASCII code shape (case-insensitive) as
one span-bearing token. Case folding is the grammar's concern: the token
is emitted uppercase so the rule is a pure table lookup. Syntax only.
BoundarySpec.WORD_SIGN blocks sign-adjacent tokens (mirrors Money's code
grammar). Suppressible short-code matcher (ADR-0009 §16).
"""

from __future__ import annotations

from paxman.capabilities.Currency.notation import CurrencyNotation
from paxman.core.grammar import AnchorSet, BoundarySpec, PipelineGrammar, StandardPre
from paxman.core.grammar.matchers.regex import RegexMatcher
from paxman.core.grammar.scan_context import ScanContext


def _emit(span: tuple[int, int], ctx: ScanContext) -> CurrencyNotation:
    s, e = span
    raw = ctx.text[s:e]
    return CurrencyNotation(text=raw.upper(), shape="code")


_MATCHER = RegexMatcher(
    pattern=r"[A-Za-z]{3}",
    boundary=BoundarySpec.WORD_SIGN,
    view=None,
    anchors=AnchorSet(),
    emit=_emit,
    suppressible=True,
)


class CodeRecognition(PipelineGrammar[CurrencyNotation]):
    """Recognizes standalone ISO 4217 alpha-3 code shapes.

    Matches a 3-letter ASCII code in any casing: "USD", "usd", "Gbp".
    The grammar folds the token to uppercase at recognition; the rule
    validates against CURRENCY_CODES. Sign characters ('-', U+2212, '+')
    are outside the identifier grammar; the word_sign boundary guards
    reject sign-adjacent tokens (mirrors Money's code grammar).

    Examples: "USD" -> text "USD", shape "code"
              "usd" -> text "USD", shape "code"
    Non-examples: "USD500"/"USD-500" (amount/sign-glued: blocked by the
        lookarounds), "xUSD" (inside a longer token).
    """

    name = "code_recognition"
    semantics = "code_recognition"
    single_value = True

    pre = StandardPre[CurrencyNotation](empty_guard=True)
    matchers = (_MATCHER,)
