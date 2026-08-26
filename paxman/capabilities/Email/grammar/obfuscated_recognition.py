"""Obfuscated email recognition grammar (staged pipeline).

Recognizes "user at domain dot tld" and "user at domain.tld". The two legacy
patterns (dot-form and at-only form) are merged into one alternation; the
notation factory branches on which alternative matched. Word boundaries are
kept verbatim (``\\b`` is a word boundary, not a hard-coded lookaround class —
ADR-0009 §10). Syntax only: the grammar never validates the address.

Keywords "at" and "dot" are matched case-insensitively (``re.IGNORECASE``)
so ``USER AT EXAMPLE DOT COM`` and ``User At Example Dot Com`` are
recognized; local/domain casing is preserved in the notation and the
domain is lowercased at validation (``Rule.normalize``). Shares
``rfc5322_addr_spec`` semantics with ``StandardEmailGrammar`` — same
validation path. Known limitation: chained ``dot`` like
``user at example dot co dot uk`` consumes only the first ``dot``
(→ ``example.co``, second ``dot uk`` ignored); bracketed forms like
``user [at] example [dot] com`` are not recognized (v0.2.0 P3).
"""

from __future__ import annotations

import re

from paxman.capabilities.Email.notation import EmailNotation
from paxman.core.grammar import PipelineGrammar, RegexStage, StandardPre

# Dot-form: "user at example dot com" -> group(2).group(3).
# At-only form: "user at gmail.com" -> group(4).
_OBFUSCATED_PATTERN = (
    r"\b([A-Za-z0-9._%+-]+)\s+at\s+(?:"
    r"([A-Za-z0-9.-]+)\s+dot\s+([A-Za-z]{2,})"
    r"|"
    r"([A-Za-z0-9.-]+\.[A-Za-z]{2,})"
    r")\b"
)


def _obfuscated_notation(match: re.Match[str]) -> EmailNotation:
    """Map an obfuscated email match to its local/domain notation.

    The dot-form alternative captures the domain before "dot" and the TLD as
    separate groups; the at-only form captures the whole domain.tld as one
    group. Mirrors the legacy two-pattern recognize() byte-for-byte.
    """
    local = match.group(1)
    if match.group(2) is not None:
        domain = f"{match.group(2)}.{match.group(3)}"
    else:
        domain = match.group(4)
    return EmailNotation(local_part=local, domain_part=domain)


class ObfuscatedEmailGrammar(PipelineGrammar[EmailNotation]):
    """Obfuscated email: 'user at domain dot tld' or 'user at domain.tld'."""

    name = "obfuscated_recognition"
    semantics = "rfc5322_addr_spec"
    single_value = True

    pre = StandardPre[EmailNotation](empty_guard=True)
    regex = RegexStage[EmailNotation](
        pattern=_OBFUSCATED_PATTERN,
        notation_fn=_obfuscated_notation,
        flags=re.IGNORECASE,
    )
