"""Language recognition grammars."""

from paxman.capabilities.Language.grammar.bcp47_tag_recognition import (
    BCP47TagGrammar,
)
from paxman.capabilities.Language.grammar.language_code_recognition import (
    LanguageCodeGrammar,
)
from paxman.capabilities.Language.grammar.language_name_recognition import (
    LanguageNameGrammar,
)

__all__ = ["BCP47TagGrammar", "LanguageCodeGrammar", "LanguageNameGrammar"]
