"""MacAddress recognition grammar — scaffolded placeholder.

TODO(scaffold): replace the placeholder pattern with a real recognizer that
emits span-bearing RecognitionMatch objects.
"""

from __future__ import annotations

import re

from paxman.capabilities.MacAddress.notation import MacAddressNotation
from paxman.core.domain import Grammar, RecognitionMatch

# Placeholder pattern: never matches NON-EMPTY text (it matches only the empty
# string). TODO(scaffold): replace with the real recognition pattern.
_PATTERN = re.compile(r"$^")


class MacAddressRecognition(Grammar[MacAddressNotation]):
    """Scaffolded grammar: mac_address_recognition."""

    name = "mac_address_recognition"
    semantics = (
        "mac_address_recognition"  # TODO(scaffold): coalesce if sharing a meaning
    )
    single_value = False  # TODO(scaffold): opt in when one mention per call

    def recognize(self, text: str) -> list[RecognitionMatch[MacAddressNotation]]:
        """TODO(scaffold): return span-bearing matches for MacAddress input."""
        return []
