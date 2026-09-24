"""ASCII hostname recognition grammar — placeholder (filled in Task 4).

TODO(task-4): replace the placeholder with the real _FQDN recognizer that
emits span-bearing RecognitionMatch objects.
"""

from __future__ import annotations

from paxman.capabilities.Domain.notation import DomainNotation
from paxman.core.domain import Grammar, RecognitionMatch


class AsciiHostnameGrammar(Grammar[DomainNotation]):
    """Scaffolded grammar: ascii_hostname."""

    name = "ascii_hostname"
    semantics = "ascii_hostname"
    single_value = False  # TODO(task-4): opt in when one mention per call

    def recognize(self, text: str) -> list[RecognitionMatch[DomainNotation]]:
        """TODO(task-4): return span-bearing matches for Domain input."""
        return []
