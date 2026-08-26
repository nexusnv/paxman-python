"""International 00-prefix recognition grammar (staged pipeline).

The international prefix "00" is the ITU-T E.164 recommended prefix used
when dialing from within most countries. The digits AFTER the prefix form
the E.164 number, so this grammar produces shape="e164" with the prefix
stripped.

The leading lookbehind (via BoundaryGuard.e164_00()) excludes word
characters, ":", ".", and "+" so "10044...", "x0044...", "0.0044...", and
"+0044..." are not treated as prefixes. The trailing digit-ending lookbehind
forces the match to end on a digit so trailing separators/whitespace/
sentence punctuation are not swallowed (mirrors the E.164 grammar).
"""

from __future__ import annotations

import re

from paxman.capabilities.Phone.grammar._common import strip_separators
from paxman.capabilities.Phone.notation import PhoneNotation
from paxman.core.grammar import (
    BoundaryGuard,
    PipelineGrammar,
    RegexStage,
    StandardPre,
)

# Body: "00" then optional separators, a non-zero first digit, then digits
# with optional separators, ending on a digit. The leading lookbehind is
# supplied by BoundaryGuard.e164_00() (ADR-0009 §10) so no hard-coded
# lookaround literal remains in this file.
_INTERNATIONAL_00_BODY = r"00[\s.\-]*(?=[1-9])\d[\d\s().\-]*(?<=\d)"
_GUARD = BoundaryGuard.e164_00()
_INTERNATIONAL_00_PATTERN = _GUARD.lookbehind + _INTERNATIONAL_00_BODY


def _international_00_notation(match: re.Match[str]) -> PhoneNotation:
    """Map a 00-prefixed match to its digit-only E.164 notation (prefix stripped)."""
    return PhoneNotation(shape="e164", value=strip_separators(match.group(0)[2:]))


class International00Grammar(PipelineGrammar[PhoneNotation]):
    """Recognizes international numbers written with the 00 prefix.

    Examples: "00 44 20 7946 0958", "00442079460958"
    Non-examples: "+442079460958" (has +), "0 44 20 7946 0958" (single 0)
    """

    name = "international_00_recognition"
    semantics = "e164_international"
    single_value = True

    pre = StandardPre[PhoneNotation](empty_guard=True)
    regex = RegexStage[PhoneNotation](
        pattern=_INTERNATIONAL_00_PATTERN, notation_fn=_international_00_notation
    )
