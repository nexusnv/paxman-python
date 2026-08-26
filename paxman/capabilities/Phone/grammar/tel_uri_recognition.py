"""RFC 3966 tel-URI recognition grammar (staged pipeline).

Recognizes a tel: URI with a GLOBAL number (optional separators) and optional
";ext=" parameter. Per RFC 3966 §3.1 global numbers REQUIRE a leading "+" —
no-plus URIs are local numbers (out of scope), so this grammar does not match
them. The scheme is matched case-insensitively; the leading lookbehind (via
BoundaryGuard.word_only()) keeps "xtel:"/"hotel:" from matching the scheme.
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

# Body: "tel:" + global number (optional separators) + optional ";ext=".
# The leading lookbehind is supplied by BoundaryGuard.word_only() (ADR-0008
# ADR-0009 §10) so no hard-coded lookaround literal remains in this file.
_TEL_BODY = r"tel:\+(\d[\d\s().\-]*)(?:;ext=(\d+))?"
_GUARD = BoundaryGuard.word_only()
_TEL_URI_PATTERN = _GUARD.lookbehind + _TEL_BODY


def _tel_notation(match: re.Match[str]) -> PhoneNotation:
    """Map a tel: URI match to its digit-only notation + extension."""
    return PhoneNotation(
        shape="rfc3966",
        value=strip_separators(match.group(1), plus=True),
        extension=match.group(2) or "",
    )


class TelUriGrammar(PipelineGrammar[PhoneNotation]):
    """Recognizes RFC 3966 tel: URIs.

    Examples: "tel:+15551234567", "tel:+1-201-555-0123;ext=890"
    Non-examples: "+15551234567" (no tel: scheme)
    """

    name = "tel_uri_recognition"
    semantics = "tel_uri_recognition"
    single_value = True

    pre = StandardPre[PhoneNotation](empty_guard=True)
    regex = RegexStage[PhoneNotation](
        pattern=_TEL_URI_PATTERN, notation_fn=_tel_notation, flags=re.IGNORECASE
    )
