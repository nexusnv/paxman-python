"""UNSPSC recognition grammar — scaffolded placeholder.

TODO(scaffold): replace the placeholder pattern with a real recognizer that
emits span-bearing RecognitionMatch objects.
"""

from __future__ import annotations

import re

from paxman.capabilities.UNSPSC.notation import UNSPSCNotation
from paxman.core.domain import Grammar, RecognitionMatch

# Placeholder pattern: never matches NON-EMPTY text (it matches only the empty
# string). TODO(scaffold): replace with the real recognition pattern.
_PATTERN = re.compile(r"$^")


class UNSPSCRecognition(Grammar[UNSPSCNotation]):
    """Scaffolded grammar: unspsc_recognition."""

    name = "unspsc_recognition"
    semantics = "unspsc_recognition"  # TODO(scaffold): coalesce if sharing a meaning
    single_value = False  # TODO(scaffold): opt in when one mention per call

    def recognize(self, text: str) -> list[RecognitionMatch[UNSPSCNotation]]:
        """TODO(scaffold): return span-bearing matches for UNSPSC input."""
        return []
