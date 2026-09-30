"""UNSPSC recognition grammar (staged pipeline).

Recognizes 6/8/10-digit UNSPSC codes with an optional fused ``UNSPSC``
label (case-insensitive, optional ``code`` word, ``:#|-.`` separators)
and the Stibo ``UNSPSC000.`` MDM lane. Longest-first alternation (10
before 8 before 6) keeps a 10-digit business-function code from carving
an 8-digit prefix within this single grammar. Internal separators
(spaces, dots, hyphens) are never tolerated: the wire form is
digits-only per every primary (Wikidata ``\\d{8}(\\d{2})?``, SAP
"eight-digit numbers", O*NET ``Decimal(8,0)``).
"""

from __future__ import annotations

import re

from paxman.capabilities.UNSPSC.notation import UNSPSCNotation
from paxman.core.grammar import PipelineGrammar, RegexStage, StandardPre

_LOOKBEHIND = r"(?<!\d)(?<![A-Za-z])(?<!\d-)"
_LOOKAHEAD = r"(?!\d)(?![A-Za-z])"
_UNSPSC_LABEL = r"(?:UNSPSC(?:0*\.?)?(?:\s+code)?[\s:#|\-.]*?)?"
_UNSPSC_BODY = (
    r"(?P<ten>\d{8}(?P<function>\d{2}))"
    r"|(?P<eight>\d{8})"
    r"|(?P<six>\d{6})"
)
_UNSPSC_PATTERN = (
    _LOOKBEHIND
    + _UNSPSC_LABEL
    + r"(?P<code>"
    + _UNSPSC_BODY
    + r")"
    + _LOOKAHEAD
    + r"(?![-]\d)"
)
# Trailing (?![-]\d) mirrors the ISBN-13 fix: a hyphen+digit continuation
# (e.g. "44103103-14", an attempted hyphenated BFI suffix) means the digit
# run is not a standalone code — no carving. The symmetric (?<!\d-)
# lookbehind rejects a digit-hyphen prefix (e.g. "44-44103103", an
# attempted hyphen-grouped code): hyphens are not UNSPSC separators on
# either side. Dot+digit still matches the stem ("44103103.0" float damage
# leaves ".0" outside the span).


def _unspsc_notation(match: re.Match[str]) -> UNSPSCNotation:
    """Map a UNSPSC match to its stem + level/function facets."""
    spelled = re.sub(r"\D", "", match.group("code"))
    raw = spelled + "00" if len(spelled) == 6 else spelled
    stem = raw[:8]
    function = raw[8:10] if len(raw) == 10 else ""
    if stem.endswith("000000"):
        level = "segment"
    elif stem.endswith("0000"):
        level = "family"
    elif stem.endswith("00"):
        level = "class"
    else:
        level = "commodity"
    return UNSPSCNotation(
        digits=stem,
        level=level,
        function=function,
        native_length=len(spelled),
    )


class UNSPSCRecognitionGrammar(PipelineGrammar[UNSPSCNotation]):
    """UNSPSC recognition: 6/8/10-digit codes with optional UNSPSC label."""

    name = "unspsc_recognition"
    semantics = "unspsc_recognition"
    single_value = True

    pre = StandardPre[UNSPSCNotation](empty_guard=True)
    regex = RegexStage[UNSPSCNotation](
        pattern=_UNSPSC_PATTERN,
        notation_fn=_unspsc_notation,
        flags=re.IGNORECASE | re.ASCII,
    )
