"""Email notation types."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class EmailNotation:
    """Email notation: local_part and domain_part.

    Frozen, slots-based notation for the email domain. ``local_part``
    is the dot-atom candidate before ``@`` and ``domain_part`` is the
    domain candidate after ``@``. Grammars split on ``@`` and rules
    own validation per RFC 5322 §3.4.1 (local/domain) and RFC 6761 §6.3
    (localhost).
    """

    local_part: str
    domain_part: str
