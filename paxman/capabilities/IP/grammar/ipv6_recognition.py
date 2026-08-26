"""IPv6 recognition grammar (staged pipeline).

Extracts IPv6 addresses in full and compressed formats. The full and
compressed legacy patterns are merged into one alternation wrapped by a
single outer capture group; the boundary lookarounds are supplied by
BoundaryGuard.ipv6_token() (ADR-0009 §10) so no hard-coded lookaround literal
remains in this file. Syntax only: the grammar never validates the address.

Note: The legacy bespoke ``recognize()`` ran two separate ``finditer`` loops
(full before compressed), so grouped matches by address family rather than
document order (e.g. ``"2001:db8:85a3::8a2e:370:7334 ::1"`` yielded
``[full, ::1]`` regardless of positions). The staged
``(_IPV6_FULL_INNER|_IPV6_COMPRESSED_INNER)`` alternation uses a single
``finditer`` in document order. The engine sorts by ``start`` before dedup,
so end-to-end ``canonicalize()`` is identical; direct ``recognize()`` order
is now document-order.
"""

from __future__ import annotations

import re

from paxman.capabilities.IP.notation import IPNotation
from paxman.core.grammar import BoundaryGuard, PipelineGrammar, RegexStage, StandardPre

# Full form: 8 groups of 1-4 hex digits separated by single colons.
_IPV6_FULL_INNER = r"[0-9a-fA-F]{1,4}(?::[0-9a-fA-F]{1,4}){7}"
# Compressed forms: handles :: with groups on either side, loopback, link-local,
# and all-zeros. Each branch is a zero-width-boundary-free inner alternative.
_IPV6_COMPRESSED_INNER = (
    r"(?:[0-9a-fA-F]{1,4}:){0,6}[0-9a-fA-F]{0,4}::"
    r"(?:[0-9a-fA-F]{0,4}:){0,6}[0-9a-fA-F]{1,4}"
    r"|"
    r"::(?:[0-9a-fA-F]{1,4}:){0,6}[0-9a-fA-F]{1,4}"
    r"|"
    r"(?:[0-9a-fA-F]{1,4}:){1,6}[0-9a-fA-F]{0,4}::"
    r"|"
    r"::"
)
# One outer capture group so the address is always group("addr"), mirroring the
# legacy recognize() (FULL used group(1), COMPRESSED used group(0) == address).
# Using a named group prevents future inner captures from shifting the index.
_IPV6_BODY = r"(?P<addr>" + _IPV6_FULL_INNER + r"|" + _IPV6_COMPRESSED_INNER + r")"

_GUARD = BoundaryGuard.ipv6_token()
_IPV6_PATTERN = _GUARD.lookbehind + _IPV6_BODY + _GUARD.lookahead


def _ipv6_notation(match: re.Match[str]) -> IPNotation:
    """Map an IPv6 match to its address notation (the outer capture group)."""
    return IPNotation(address=match.group("addr"))


class IPv6Grammar(PipelineGrammar[IPNotation]):
    """IPv6 recognition: full and compressed formats.

    Handles:
    - Full form: 2001:0db8:85a3:0000:0000:8a2e:0370:7334
    - Compressed: 2001:db8:85a3::8a2e:370:7334
    - Loopback: ::1
    - Link-local: fe80::1
    - All-zeros: ::
    """

    name = "ipv6_recognition"
    semantics = "ipv6_recognition"
    single_value = True

    pre = StandardPre[IPNotation](empty_guard=True)
    regex = RegexStage[IPNotation](pattern=_IPV6_PATTERN, notation_fn=_ipv6_notation)
