"""NANP national number recognition grammar (staged pipeline).

Recognizes domestic (NANP-style) dialing formats: optional trunk "1",
optional parenthesized NPA, then 3-3-4 digit groups with any of space,
dash, or dot separators. This grammar is deliberately NANP-shaped for
Milestone 1; future milestones add country-specific national grammars.
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

# Optional trunk 1, optional (NPA), NXX, XXXX. NPA first digit 2-9 is a
# recognition heuristic — strict validation (including NXX first digit 2-9)
# happens in the rules. NXX is deliberately loose here so the grammar
# recognizes the NANP *shape* even for unassignable exchanges (e.g.
# "555-123-4567"), which the NANP rule then rejects as INVALID.
#
# The four fixed-width negative lookbehinds (via BoundaryGuard.phone_national())
# ensure this grammar does NOT match inside E.164 numbers or tel: URIs (those
# belong to the e164 / tel-URI grammars). They reject a match when the
# characters immediately before it belong to an international number. The
# trailing lookahead (also from the guard) rejects a digit immediately after
# the number. No hard-coded lookaround literal remains in this file (ADR-0008
# ADR-0009 §10).
_NATIONAL_BODY = r"(?:1[\s.\-]?)?\(?([2-9]\d{2})\)?[\s.\-]?(\d{3})[\s.\-]?(\d{4})"
_GUARD = BoundaryGuard.phone_national()
_NATIONAL_PATTERN = _GUARD.lookbehind + _NATIONAL_BODY + _GUARD.lookahead


def _national_notation(match: re.Match[str]) -> PhoneNotation:
    """Map a national match to its digit-only notation (trunk 1 preserved)."""
    return PhoneNotation(shape="national", value=strip_separators(match.group(0)))


class NationalGrammar(PipelineGrammar[PhoneNotation]):
    """Recognizes NANP national dialing formats.

    Examples: "(555) 123-4567", "555-123-4567", "1-555-123-4567"
    Non-examples: "+15551234567" (international), "555-1234" (7-digit local)
    """

    name = "national_recognition"
    semantics = "national_recognition"
    single_value = True

    pre = StandardPre[PhoneNotation](empty_guard=True)
    regex = RegexStage[PhoneNotation](
        pattern=_NATIONAL_PATTERN, notation_fn=_national_notation
    )
