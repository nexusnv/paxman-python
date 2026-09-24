"""IDN hostname recognition grammar — stub (filled in Task 5).

TODO(task-5): replace the stub with the real _IDN_FQDN recognizer that
emits span-bearing RecognitionMatch objects.
"""

from __future__ import annotations

from paxman.capabilities.Domain.notation import DomainNotation
from paxman.core.domain import Grammar, RecognitionMatch


class IdnHostnameGrammar(Grammar[DomainNotation]):
    """Stub grammar: idn_hostname."""

    name = "idn_hostname"
    semantics = "idn_hostname"
    single_value = False  # TODO(task-5): opt in when one mention per call

    def recognize(self, text: str) -> list[RecognitionMatch[DomainNotation]]:
        """TODO(task-5): return span-bearing matches for Domain input."""
        return []
