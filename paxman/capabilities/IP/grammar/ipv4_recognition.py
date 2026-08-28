"""IPv4 recognition grammar (staged pipeline).

Extracts dotted-decimal IPv4 addresses. The word boundaries are kept verbatim
(``\\b`` is a word boundary, not a hard-coded lookaround class —
ADR-0009 §10). Syntax only: the grammar never validates the address.
"""

from __future__ import annotations

import re

from paxman.capabilities.IP.notation import IPNotation
from paxman.core.grammar import PipelineGrammar, RegexStage, StandardPre

_IPV4_PATTERN = r"\b(\d{1,3})\.(\d{1,3})\.(\d{1,3})\.(\d{1,3})\b"


def _ipv4_notation(match: re.Match[str]) -> IPNotation:
    """Map an IPv4 match to its address notation."""
    return IPNotation(address=match.group(0))


class IPv4Grammar(PipelineGrammar[IPNotation]):
    """IPv4 recognition: dotted-decimal format (e.g., 192.168.1.1)."""

    name = "ipv4_recognition"
    semantics = "ipv4_recognition"
    single_value = True

    pre = StandardPre[IPNotation](empty_guard=True)
    regex = RegexStage[IPNotation](pattern=_IPV4_PATTERN, notation_fn=_ipv4_notation)
