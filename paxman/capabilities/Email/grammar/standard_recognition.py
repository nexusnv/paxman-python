"""Standard email recognition grammar (staged pipeline).

Recognizes user@domain.tld. The word boundaries are kept verbatim (``\\b`` is
a word boundary, not a hard-coded lookaround class — ADR-0009 §10). Syntax
only: the grammar never validates the address.
"""

from __future__ import annotations

import re

from paxman.capabilities.Email.notation import EmailNotation
from paxman.core.grammar import PipelineGrammar, RegexStage, StandardPre

_STANDARD_PATTERN = r"\b[A-Za-z0-9][A-Za-z0-9._%+-]*@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"


def _standard_notation(match: re.Match[str]) -> EmailNotation:
    """Map a standard email match to its local/domain notation."""
    local, domain = match.group(0).split("@")
    return EmailNotation(local_part=local, domain_part=domain)


class StandardEmailGrammar(PipelineGrammar[EmailNotation]):
    """Standard email recognition: user@domain.tld."""

    name = "standard_recognition"
    semantics = "rfc5322_addr_spec"
    single_value = True

    pre = StandardPre[EmailNotation](empty_guard=True)
    regex = RegexStage[EmailNotation](
        pattern=_STANDARD_PATTERN, notation_fn=_standard_notation
    )
