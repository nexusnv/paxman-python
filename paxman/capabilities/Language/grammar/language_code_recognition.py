"""Language code recognition — bare 2-3 via kernel RegexMatcher.

BoundarySpec.WORD_SIGN blocks hyphen/plus/sign so bare codes do not carve
inside BCP47 tags (e.g. ``en`` inside ``en-US`` must not be recognized as
language_code; the tag is the longer, correct recognition). Mirrors
Phone/Currency sign-aware guards for disjoint grammars within one capability.
Suppressible short-code matcher (ADR-0009 §16).

Bare 5-8 letter runs are intentionally unclaimed: the reachable valid set is
empty — the only two valid 5-8 IANA codes (no-bok/no-nyn) are hyphenated and
a hyphenless letter-run regex can never emit them. Re-add a 5-8 branch if IANA
ever registers a hyphenless 5-8 primary.
"""

from __future__ import annotations

from paxman.capabilities.Language.notation import LanguageNotation
from paxman.core.grammar import AnchorSet, BoundarySpec, PipelineGrammar, StandardPre
from paxman.core.grammar.matchers.regex import RegexMatcher
from paxman.core.grammar.scan_context import ScanContext


def _emit(span: tuple[int, int], ctx: ScanContext) -> LanguageNotation:
    """Build LanguageNotation from a bare 2-3 letter code span."""
    s, e = span
    raw = ctx.text[s:e]
    lower = raw.lower()
    return LanguageNotation(
        language=lower,
        extlang="",
        script="",
        region="",
        variant="",
        extension="",
        privateuse="",
        grandfathered="",
        compact=lower,
        raw_value=lower,
    )


_MATCHER = RegexMatcher(
    pattern=r"[A-Za-z]{2,3}",
    boundary=BoundarySpec.WORD_SIGN,
    view=None,
    anchors=AnchorSet(),
    emit=_emit,
    suppressible=True,
)


class LanguageCodeGrammar(PipelineGrammar[LanguageNotation]):
    """Bare language code recognition — 2-3 letters."""

    name = "language_code_recognition"
    semantics = "language_code"
    single_value = True

    pre = StandardPre[LanguageNotation](empty_guard=True)
    matchers = (_MATCHER,)
