"""Language recognition grammar — scaffolded placeholder.

TODO(scaffold): replace the placeholder pattern with a real recognizer that
emits span-bearing RecognitionMatch objects.
"""

from __future__ import annotations

import re

from paxman.capabilities.Language.notation import LanguageNotation
from paxman.core.domain import Grammar, RecognitionMatch

# Placeholder pattern: never matches NON-EMPTY text (it matches only the empty
# string). TODO(scaffold): replace with the real recognition pattern.
_PATTERN = re.compile(r"$^")


class LanguageRecognition(Grammar[LanguageNotation]):
    """Scaffolded grammar: language_recognition."""

    name = "language_recognition"
    semantics = "language_recognition"  # TODO(scaffold): coalesce if sharing a meaning
    single_value = False  # TODO(scaffold): opt in when one mention per call

    def recognize(self, text: str) -> list[RecognitionMatch[LanguageNotation]]:
        """TODO(scaffold): return span-bearing matches for Language input."""
        return []
