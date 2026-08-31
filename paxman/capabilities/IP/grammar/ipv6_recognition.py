"""IPv6 recognition grammar (staged pipeline).

Extracts IPv6 addresses in full, compressed, and mixed (embedded-IPv4)
formats. The full and compressed legacy patterns are merged into one
alternation wrapped by a single outer capture group; the boundary lookarounds
are supplied by BoundaryGuard.ipv6_token() (ADR-0009 §10) so no hard-coded
lookaround literal remains in this file. Syntax only: the grammar never
validates the address.

Mixed addresses per RFC 4291 §2.2 / RFC 5952 §5 (e.g. ``::ffff:192.0.2.1``,
``64:ff9b::192.0.2.1``) are recognized via two additional Las32 branches
(6 hextets + dotted-decimal, and compressed + dotted-decimal). The mixed
branches are ordered before the plain compressed branch so that
``::ffff:192.0.2.1`` is not truncated to ``::ffff:192``. See ``ipv4_recognition``
for the overlapping ``192.0.2.1`` candidate note.

Note: The legacy bespoke ``recognize()`` ran two separate ``finditer`` loops
(full before compressed), so grouped matches by address family rather than
document order (e.g. ``"2001:db8:85a3::8a2e:370:7334 ::1"`` yielded
``[full, ::1]`` regardless of positions). The staged
``(_IPV6_FULL_INNER|_IPV6_COMPRESSED_INNER|_IPV6_MIXED_*)`` alternation uses
a single ``finditer`` in document order. The engine sorts by ``start`` before
dedup, so end-to-end ``canonicalize()`` is identical; direct ``recognize()``
order is now document-order.
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
# Mixed (embedded-IPv4) per RFC 4291 §2.2 — last 32 bits as dotted-decimal.
# Two forms: 6 hextets + ipv4 (no ::), and compressed + ipv4 (with ::).
# Syntax-only: the IPv4 part uses \d{1,3} (broader than strict 0-255), as
# validation via ipaddress.IPv6Address rejects >255. Placed before the plain
# compressed alternatives to avoid truncation of ::ffff:192.0.2.1 → ::ffff:192.
_IPV4_DOTTED = r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}"
_IPV6_MIXED_FULL = r"(?:[0-9a-fA-F]{1,4}:){6}" + _IPV4_DOTTED
_IPV6_MIXED_COMPRESSED = (
    r"(?:[0-9a-fA-F]{1,4}:){0,5}[0-9a-fA-F]{0,4}::"
    r"(?:[0-9a-fA-F]{1,4}:){0,5}" + _IPV4_DOTTED
)
_IPV6_MIXED_INNER = _IPV6_MIXED_FULL + r"|" + _IPV6_MIXED_COMPRESSED
# One outer capture group so the address is always group("addr"), mirroring the
# legacy recognize() (FULL used group(1), COMPRESSED used group(0) == address).
# Using a named group prevents future inner captures from shifting the index.
# Mixed branches are ordered first to win over the truncated compressed match.
_IPV6_BODY = (
    r"(?P<addr>"
    + _IPV6_MIXED_INNER
    + r"|"
    + _IPV6_FULL_INNER
    + r"|"
    + _IPV6_COMPRESSED_INNER
    + r")"
)

_GUARD = BoundaryGuard.ipv6_token()
_IPV6_PATTERN = _GUARD.lookbehind + _IPV6_BODY + _GUARD.lookahead


def _ipv6_notation(match: re.Match[str]) -> IPNotation:
    """Map an IPv6 match to its address notation (the outer capture group)."""
    return IPNotation(address=match.group("addr"))


class IPv6Grammar(PipelineGrammar[IPNotation]):
    """IPv6 recognition: full, compressed, and mixed (embedded-IPv4) formats.

    Handles:
    - Full form: 2001:0db8:85a3:0000:0000:8a2e:0370:7334
    - Compressed: 2001:db8:85a3::8a2e:370:7334
    - Loopback: ::1
    - Link-local: fe80::1
    - All-zeros: ::
    - Mixed: ::ffff:192.0.2.1, 64:ff9b::192.0.2.1 (RFC 4291 §2.2)

    Note: For mixed addresses the trailing IPv4 dotted-decimal is also emitted
    by ``ipv4_recognition`` as a second candidate (``\\b`` boundary). The
    engine preserves both (cross-grammar dedup is not performed) so
    ``canonicalize("::ffff:192.0.2.1")`` yields two candidates; callers
    should prefer the IPv6 value. See issue #113 B1.
    """

    name = "ipv6_recognition"
    semantics = "ipv6_recognition"
    single_value = True

    pre = StandardPre[IPNotation](empty_guard=True)
    regex = RegexStage[IPNotation](pattern=_IPV6_PATTERN, notation_fn=_ipv6_notation)
