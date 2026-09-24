"""Timezone abbreviation recognition grammar — refused shorthand tokens.

UPPER-exact lexicon over the carved short-caps Links plus the
ambiguous refusal set, with WORD guards on both sides (bare ``EST``
in prose claims; ``ESTIMATE`` must not). No folded view by design —
lowercase ``est`` is an ordinary word, not a zone mention. Every
claim carries family ``"abbreviation"``; the rule refuses them all
(never a silent pick). ``UTC``/``GMT`` are zone-defined fixed zones,
never abbreviations, and are exempt here.

Tokens below mirror ``abbreviation_map`` (carved Links + refusal
set), uppercased; keys only, never a mapping — the grammar tests
assert parity with that table, and this module imports nothing from
``rules`` (grammar/rule separation is structural).
"""

from __future__ import annotations

from paxman.capabilities.Timezone.notation import TimezoneNotation
from paxman.core.grammar import (
    AnchorSet,
    BoundarySpec,
    PipelineGrammar,
    StandardPre,
)
from paxman.core.grammar.matchers.lexicon import LexiconMatcher
from paxman.core.grammar.scan_context import ScanContext

# UPPER-exact abbreviation tokens: carved short-caps Links
# (EST/MST/HST/CET) + ambiguous refusals (IST/CST/PST).
ABBREVIATION_TOKENS: frozenset[str] = frozenset(
    {
        "CET",
        "CST",
        "EST",
        "HST",
        "IST",
        "MST",
        "PST",
    }
)


def _emit(span: tuple[int, int], ctx: ScanContext) -> TimezoneNotation:
    """Emit an abbreviation-family notation preserving the token."""
    s, e = span
    raw = ctx.text[s:e]
    return TimezoneNotation(key=raw, family="abbreviation", compact=raw)


_ABBREVIATION_MATCHER = LexiconMatcher(
    tokens=ABBREVIATION_TOKENS,
    boundary=BoundarySpec.WORD,
    view=None,
    anchors=AnchorSet(),
    emit=_emit,
)


class TimezoneAbbreviationGrammar(PipelineGrammar[TimezoneNotation]):
    """Recognizes bare timezone abbreviations, case-exact UPPER.

    Emits the as-written token with family ``"abbreviation"``; rules
    own refusal with provenance.

    Examples: "EST" → key="EST"
              "arrive CET tomorrow" → key="CET" span (7, 10)
    Non-examples: "est" → [] (case-exact)
                  "ESTIMATE" → [] (WORD guards)
                  "UTC" → [] (fixed zone, name family)
                  "XYZ" → [] (unlisted)
    """

    name = "timezone_abbreviation_recognition"
    semantics = "timezone_abbreviation"
    single_value = True

    pre = StandardPre[TimezoneNotation](empty_guard=True)
    matchers = (_ABBREVIATION_MATCHER,)
