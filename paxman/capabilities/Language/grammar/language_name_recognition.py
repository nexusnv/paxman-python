"""Language name recognition — WholeInputLookup union ENGLISH + LOCALIZED."""

from __future__ import annotations

from paxman.capabilities.Language.grammar.data.english_names import (
    ENGLISH_LANGUAGE_KEYS,
)
from paxman.capabilities.Language.grammar.data.localized_names import (
    LOCALIZED_LANGUAGE_KEYS,
)
from paxman.capabilities.Language.notation import LanguageNotation, normalize_name
from paxman.core.grammar import PipelineGrammar, StandardPre, WholeInputLookup

_KNOWN_LANGUAGE_KEYS: frozenset[str] = frozenset(
    ENGLISH_LANGUAGE_KEYS | LOCALIZED_LANGUAGE_KEYS
)


def _name_notation(trimmed: str) -> LanguageNotation:
    lower = trimmed.lower()
    return LanguageNotation(
        language="",
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


class LanguageNameGrammar(PipelineGrammar[LanguageNotation]):
    """Lexicon language name recognition — whole-input lookup."""

    name = "language_name_recognition"
    semantics = "language_name"
    single_value = True

    pre = StandardPre[LanguageNotation](empty_guard=True)
    lexicon = WholeInputLookup[LanguageNotation](
        keys=_KNOWN_LANGUAGE_KEYS,
        normalizer=normalize_name,
        notation_fn=_name_notation,
    )
