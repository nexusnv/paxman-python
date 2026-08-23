"""ORCID recognition grammar — scaffolded placeholder.

TODO(scaffold): replace the placeholder pattern with a real recognizer that
emits span-bearing RecognitionMatch objects.
"""

from __future__ import annotations

import re

from paxman.capabilities.ORCID.notation import ORCIDNotation
from paxman.core.domain import Grammar, RecognitionMatch

# Placeholder pattern: never matches NON-EMPTY text (it matches only the empty
# string). TODO(scaffold): replace with the real recognition pattern.
_PATTERN = re.compile(r"$^")


class ORCIDRecognition(Grammar[ORCIDNotation]):
    """Scaffolded grammar: orcid_recognition."""

    name = "orcid_recognition"
    semantics = "orcid_recognition"  # TODO(scaffold): coalesce if sharing a meaning
    single_value = False  # TODO(scaffold): opt in when one mention per call

    def recognize(self, text: str) -> list[RecognitionMatch[ORCIDNotation]]:
        """TODO(scaffold): return span-bearing matches for ORCID input."""
        return []
