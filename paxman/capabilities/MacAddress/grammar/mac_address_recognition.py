"""MAC address recognition - EUI-48/EUI-64, 4 separator families, fused MAC label."""

from __future__ import annotations

import re

from paxman.capabilities.MacAddress.notation import MacAddressNotation
from paxman.core.grammar.boundary import BoundaryGuard
from paxman.core.grammar.pipeline import PipelineGrammar
from paxman.core.grammar.stages import RegexStage, StandardPre

# 2-hex octet / 4-hex hextet building blocks. Case handling is delegated to
# the (?ai:...) inline group (ASCII + IGNORECASE), exactly like the shipped
# BIC grammar; [0-9A-F] classes therefore accept a-f too.
_OCTET = r"[0-9A-F]{2}"
_HEXTET = r"[0-9A-F]{4}"

# Separator families are internally consistent per branch: each branch
# hard-codes its separator, so mixed-separator input ("00:1A-2B:...") can
# never match - the Python-re equivalent of validator.js's backreference \1
# and Go's single-separator dispatch, without group-number collisions across
# alternation branches.
_EUI48_COLON = rf"(?:{_OCTET}:){{5}}{_OCTET}"
_EUI64_COLON = rf"(?:{_OCTET}:){{7}}{_OCTET}"
_EUI48_HYPHEN = rf"(?:{_OCTET}-){{5}}{_OCTET}"
_EUI64_HYPHEN = rf"(?:{_OCTET}-){{7}}{_OCTET}"
_EUI48_DOT = rf"(?:{_HEXTET}\.){{2}}{_HEXTET}"
_EUI64_DOT = rf"(?:{_HEXTET}\.){{3}}{_HEXTET}"

# Bare forms split by length so the truncation guard can be applied to the
# 48-bit side only: 16 hex (4 hextets, tried first) and 12 hex (6 octets).
_BARE16 = rf"{_HEXTET}{_HEXTET}{_HEXTET}{_HEXTET}"
_BARE12 = rf"{_OCTET}{_OCTET}{_OCTET}{_OCTET}{_OCTET}{_OCTET}"

# Truncation guard (48-bit branches only): a 6-octet / 12-hex claim must not
# stand when immediately followed by a separator + exactly 2 terminating hex
# digits - the signature of a truncated final octet of a longer run
# ("00:1A:2B:3C:4D:5E:66" is a malformed 8-octet address, not a 6-octet one
# plus junk). The outer lookahead cannot see this: ':'/'-'/'.' are not \w.
# EUI-64 claims are EXEMPT: "84:71:27:ff:fe:93:17:24-11" (Home Assistant's
# "{ieee}-{endpoint_id}" device_config key shape) must keep claiming the
# 8-octet address with the endpoint suffix as residue.
_TRUNCATION_GUARD = r"(?!(?ai:[-:.][0-9A-F]{2}(?!\w)))"

# Branch ordering: all four 64-bit forms precede all four 48-bit forms and
# the 16-hex bare precedes the 12-hex bare, so finditer consumes the longest
# span at each scan position. The engine's within-grammar containment dedup
# ("longer wins", orchestrator:_dedup_spans) is the second safety net: any
# shorter same-start match (e.g. the EUI-48 prefix of an EUI-64) is fully
# contained in the emitted longer match and dropped. This is why ONE grammar
# must own both lengths - two grammars would preserve cross-grammar
# containment and produce spurious AMBIGUOUS with 12-hex vs 16-hex values.
_64_ALTS = "|".join([_EUI64_COLON, _EUI64_HYPHEN, _EUI64_DOT, _BARE16])
_48_ALTS = "|".join([_EUI48_COLON, _EUI48_HYPHEN, _EUI48_DOT, _BARE12])
_BODY_ALTS = f"{_64_ALTS}|(?:{_48_ALTS}){_TRUNCATION_GUARD}"

# Optional fused label: (?ai:MAC)[\s:-]+ one-or-more, never zero width
# (BIC/ISSN/IBAN label precedent). "MAC001A2B3C4D5E" (glued) cannot match:
# the label branch requires a separator, and no body branch can start at
# "M" (not a hex digit) or carve after it (word_only lookbehind sees \w).
_MAC_BODY = rf"(?ai:(?:(?:MAC)[\s:-]+)?(?P<compact>(?:{_BODY_ALTS})))"

# Mid-run guard (mac_midrun() factory, phone_national() precedent): word_only
# alone treats ':'/'-'/'.' as boundaries, so the TAIL of a longer colon run
# would be claimed as a fresh 6-octet match ("00:1A:2B:3C:4D:5E:66" must not
# yield "1A:2B:3C:4D:5E:66"). The second stacked lookbehind rejects a claim
# start preceded by hex + separator. It constrains only the MATCH START, so
# the fused label case is unaffected ("MAC:00:1A:..." starts at the M).
_MAC_GUARD = BoundaryGuard.mac_midrun()

_MAC_PATTERN = _MAC_GUARD.lookbehind + _MAC_BODY + _MAC_GUARD.lookahead


def _mac_notation(match: re.Match[str]) -> MacAddressNotation:
    raw_compact = match.group("compact")
    compact = "".join(ch for ch in raw_compact if ch.isascii() and ch.isalnum()).upper()
    shape = "eui64" if len(compact) == 16 else "eui48"
    return MacAddressNotation(compact=compact, shape=shape)


class MacAddressRecognitionGrammar(PipelineGrammar[MacAddressNotation]):
    """MAC address recognition - EUI-48/EUI-64, colon/hyphen/tri-dot/bare.

    Recognizes all eight shape families (4 separators x 2 lengths, bare
    split 16-before-12). Case-insensitive; notation strips separators via
    isascii()/isalnum() and uppercases. One consistent separator per mention
    by construction. Does not interpret U/L or I/G bits and does not check
    OUI membership - rules own that. Bit-reversed (Token-Ring/FDDI) spellings
    are recognized as themselves; no bit-order reinterpretation anywhere.
    """

    name = "mac_address_recognition"
    semantics = "mac_address_recognition"
    single_value = True
    pre = StandardPre[MacAddressNotation](empty_guard=True)
    regex = RegexStage[MacAddressNotation](
        pattern=_MAC_PATTERN, notation_fn=_mac_notation
    )


# Backward compat alias for scaffolder capability import (Task 0); will be
# removed when capability.py is wired in Task 5.
MacAddressRecognition = MacAddressRecognitionGrammar
