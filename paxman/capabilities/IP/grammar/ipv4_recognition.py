"""IPv4 recognition grammar (staged pipeline).

Extracts dotted-decimal IPv4 addresses. The word boundaries are kept verbatim
(``\\b`` is a word boundary, not a hard-coded lookaround class —
ADR-0009 §10). Syntax only: the grammar never validates the address (e.g.
``999.999.999.999`` is emitted and rejected by the ``Section 3.2`` rule).
Leading-zero forms such as ``010.020.030.040`` are recognized and later
normalized to ``10.20.30.40``. The ``\\b`` tokenization means the trailing
IPv4 inside an IPv6 mixed address (``::ffff:192.0.2.1``) is intentionally
also emitted as a second candidate — see ``ipv6_recognition`` for the
mixed-form grammar and the overlap note.
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
