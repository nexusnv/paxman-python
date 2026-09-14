"""UtcOffset recognition grammar — human-notation numeric offsets.

Regex over documented human semantics (never POSIX sign-flipped):
optional ``UTC``/``GMT`` prefix (any case), ``±HH`` / ``±HHMM`` /
``±HH:MM``, and the ``Z`` designator. Word guards on the right plus a
slash-aware lookbehind on the left (``[\\w/]`` — a ``BoundarySpec``
composition): no offset is carved out of a zone key, so ``Etc/GMT+5``
belongs solely to the Timezone name grammar.

Emit normalizes to canonical extended ``+HH:MM`` (zero-padded,
``Z`` → ``+00:00``). ``-00:00`` is emitted here — grammar claims
shape, the rule refuses it (unknown-offset is ignorance, not zero).
"""

from __future__ import annotations

import re

from paxman.capabilities.UtcOffset.notation import UtcOffsetNotation
from paxman.core.grammar import (
    AnchorSet,
    BoundarySpec,
    PipelineGrammar,
    StandardPre,
)
from paxman.core.grammar.matchers.regex import RegexMatcher
from paxman.core.grammar.scan_context import ScanContext

_OFFSET_BODY = r"(?:UTC|GMT)?[+-](?:1[0-4]|0?\d)(?::?[0-5]\d)?|[Zz]"

# Slash-aware lookbehind (no mid-key extraction) + hardened right edge:
# no word char (glued runs), no colon (partial minutes like +05:6* or
# trailing seconds), no sign (dangling continuations). A truncated
# prefix never emits: +05:60, +05:00:00, ++05:00 all MISSING.
_OFFSET_BOUNDARY = BoundarySpec(
    left=(r"[\w/]", r"[+-]"),
    right=(r"\w", r":", r"[+-]"),
    mode="zero_width",
)

_OFFSET_RE = re.compile(r"^(?:UTC|GMT)?([+-])(\d{1,2})(?::?(\d{2}))?$", re.IGNORECASE)


def _offset_emit(span: tuple[int, int], ctx: ScanContext) -> UtcOffsetNotation:
    s, e = span
    raw = ctx.text[s:e]
    if raw in ("Z", "z"):
        return UtcOffsetNotation(compact="+00:00")
    parsed = _OFFSET_RE.fullmatch(raw)
    if parsed is None:  # Unreachable via _OFFSET_BODY; never raise.
        return UtcOffsetNotation(compact=raw)
    sign, hour, minute = parsed.group(1), parsed.group(2), parsed.group(3)
    return UtcOffsetNotation(
        compact=f"{sign}{int(hour):02d}:{minute if minute is not None else '00'}"
    )


_OFFSET_MATCHER = RegexMatcher(
    pattern=_OFFSET_BODY,
    flags=re.IGNORECASE,
    boundary=_OFFSET_BOUNDARY,
    view=None,
    anchors=AnchorSet(),
    emit=_offset_emit,
)


class UtcOffsetGrammar(PipelineGrammar[UtcOffsetNotation]):
    """Recognizes human-notation UTC offsets and normalizes to +HH:MM.

    Examples: "UTC+5" → compact="+05:00"
              "+0530" → compact="+05:30"
              "Z" → compact="+00:00"
              "-00:00" → compact="-00:00" (rule refuses)
    Non-examples: "Etc/GMT+5" → [] (zone key, slash guard)
                  "Zulu" → [] (WORD guards)
                  "XUTC+5" → [] (glued run)
    """

    name = "utc_offset_recognition"
    semantics = "utc_offset"
    single_value = True

    pre = StandardPre[UtcOffsetNotation](empty_guard=True)
    matchers = (_OFFSET_MATCHER,)
