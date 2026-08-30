"""Localhost email recognition grammar (staged pipeline).

Recognizes user@localhost. The word boundary and trailing lookahead are kept
verbatim (``\\b`` is a word boundary, not a hard-coded lookaround class —
ADR-0009 §10). Syntax only: the grammar never validates the address.

Port ``:(digits)`` is syntax but stripped for validation: the notation
is always ``domain_part="localhost"`` (lowercase) regardless of input
case or port. ``raw_text`` preserves the matched ``user@localhost:8080``
span; ``normalize`` emits ``local@localhost`` only. Non-digit ports like
``:abc`` break the match → ``MISSING``; digit ports are swallowed in the
span but ignored for validation.
"""

from __future__ import annotations

import re

from paxman.capabilities.Email.notation import EmailNotation
from paxman.core.grammar import PipelineGrammar, RegexStage, StandardPre

_LOCALHOST_PATTERN = (
    r"\b([A-Za-z0-9._%+-]+)@localhost(?::\d+)?(?:(?=[\s,;()]|$)|\.(?=\s|$))"
)


def _localhost_notation(match: re.Match[str]) -> EmailNotation:
    """Map a localhost email match to its local/localhost notation."""
    return EmailNotation(local_part=match.group(1), domain_part="localhost")


class LocalhostEmailGrammar(PipelineGrammar[EmailNotation]):
    """Localhost email recognition: user@localhost."""

    name = "localhost_recognition"
    semantics = "localhost_recognition"
    single_value = True

    pre = StandardPre[EmailNotation](empty_guard=True)
    regex = RegexStage[EmailNotation](
        pattern=_LOCALHOST_PATTERN, notation_fn=_localhost_notation, flags=re.IGNORECASE
    )
