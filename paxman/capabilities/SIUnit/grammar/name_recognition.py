"""Name recognition grammar for SI Unit (lexicon trie).

Recognizes unit names case-insensitively: the grammar folds the input
to lowercase and matches against the longest-first name token table
(D4). "Kilogram", "KILOGRAM", "kilogram" all emit a RecognitionMatch
over the span of the name text. Recognition only: no validation.

Migrated from RegexStage with BoundaryGuard.degree_word_sign (re.IGNORECASE)
to a lexicon trie on the CaseFold view. The split-prefix shape
("kilo gram" -> ``split_word_prefix``) is computed via the token's
first-word check, byte-identically to the legacy ``recognize()``.
"""

from __future__ import annotations

from paxman.capabilities.SIUnit.grammar.data.prefix_tokens import PREFIX_WORD_TOKENS
from paxman.capabilities.SIUnit.grammar.data.unit_name_tokens import NAME_TOKENS
from paxman.capabilities.SIUnit.notation import SIUnitNotation
from paxman.core.domain import RecognitionMatch
from paxman.core.grammar import (
    AnchorSet,
    BoundarySpec,
    PipelineGrammar,
    StandardPre,
)
from paxman.core.grammar.matchers.lexicon import LexiconMatcher
from paxman.core.grammar.normalizers import CaseFold
from paxman.core.grammar.scan_context import ScanContext

PREFIX_WORDS = frozenset(PREFIX_WORD_TOKENS)

_BASE_NAME_TOKENS: frozenset[str] = frozenset(NAME_TOKENS)
_SPACED_NAME_TOKENS: frozenset[str] = frozenset(
    f"{p} {n}" for p in PREFIX_WORD_TOKENS for n in NAME_TOKENS
)
_ALL_NAME_TOKENS: frozenset[str] = _BASE_NAME_TOKENS | _SPACED_NAME_TOKENS


def _emit_name(span: tuple[int, int], ctx: ScanContext) -> SIUnitNotation:
    s, e = span
    token = ctx.text[s:e].lower()
    parts = token.split()
    if len(parts) >= 2 and parts[0] in PREFIX_WORDS:
        shape = "split_word_prefix"
    else:
        shape = "name"
    return SIUnitNotation(text=token, shape=shape)


_NAME_MATCHER = LexiconMatcher(
    tokens=_ALL_NAME_TOKENS,
    boundary=BoundarySpec.DEGREE_WORD_SIGN,
    view="casefolded",
    anchors=AnchorSet(),
    emit=_emit_name,
    representation="auto",
)


class NameRecognition(PipelineGrammar[SIUnitNotation]):
    """Grammar: name_recognition — case-folded unit names."""

    name = "name_recognition"
    semantics = "name_recognition"

    pre = StandardPre[SIUnitNotation](empty_guard=True)
    matchers = (_NAME_MATCHER,)

    def recognize(self, text: str) -> list[RecognitionMatch[SIUnitNotation]]:
        if not text.strip():
            return []
        ctx = ScanContext.of(text)
        view = ctx.view("casefolded", CaseFold().normalize)
        spans = _NAME_MATCHER.match(view)
        out: list[RecognitionMatch[SIUnitNotation]] = []
        for s, e in spans:
            o_s, o_e = view.original_span(s, e)
            raw = text[o_s:o_e]
            token = raw.lower()
            parts = token.split()
            if len(parts) >= 2 and parts[0] in PREFIX_WORDS:
                shape = "split_word_prefix"
            else:
                shape = "name"
            out.append(
                RecognitionMatch(
                    notation=SIUnitNotation(text=token, shape=shape),
                    start=o_s,
                    end=o_e,
                    raw_text=raw,
                )
            )
        return out
