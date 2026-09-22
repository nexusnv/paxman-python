"""GTIN recognition — LabelMatcher with exact-length digit alternation.

Single ``gtin_recognition`` grammar (ISBN shape): fused
``GTIN/UPC/EAN`` labels + ``(01)``/``AI 01`` branch, separator-tolerant
exact-length alternation (8/12/13/14, longest-first), label/AI-strip emit,
glued-``reject``, WORD guards.
"""

from __future__ import annotations

import re

from paxman.capabilities.GTIN.notation import GTINNotation
from paxman.core.grammar import BoundarySpec, PipelineGrammar, StandardPre
from paxman.core.grammar.anchors import HasDigit
from paxman.core.grammar.matchers.label import LabelMatcher
from paxman.core.grammar.scan_context import ScanContext

_GTIN_LABELS = frozenset(
    {
        "GTIN",
        "GTIN-8",
        "GTIN-12",
        "GTIN-13",
        "GTIN-14",
        "UPC",
        "UPC-A",
        "EAN",
        "EAN-8",
        "EAN-13",
    }
)

_GTIN_LABEL_RE = re.compile(
    r"^(?:GTIN(?:-8|-12|-13|-14)?|UPC(?:-A)?|EAN(?:-8|-13)?)[\s:-]+",
    re.IGNORECASE,
)

_GTIN_AI_RE = re.compile(
    r"^(?:\(01\)[\s:-]*|AI\s+01[\s:-]+)",
    re.IGNORECASE,
)

# Exact-length alternation, longest-first: 14/13/12/8 digits with
# space/hyphen tolerance. 6/7/9/10/11/15+ are unmatchable by construction.
# The (01)/AI 01 prefix nests only in the 14-digit branch (GS1 AI 01
# carries a 14-digit field); 13/12/8-digit branches are unprefixed.
# Trailing (?![-]\d) blocks hyphen-digit continuation (ISBN-13 precedent).
# Trailing (?!\w) mirrors the WORD boundary's right guard inside the
# regex (ASCII input; fullwidth/non-ASCII runs are rejected upstream):
# a run-on arm (single space between two mentions lets the 14-digit
# alternation reach into the next mention) fails the lookahead and the
# engine backtracks to the shorter arm at the SAME start. Without it the
# matcher only rejects the run-on after matching and resumes past the
# start, losing the first mention entirely ("5012345670003 614141999996"
# would recognize only the second GTIN).
_GTIN_BODY = (
    r"(?:(?:\(01\)[\s:-]*|AI\s+01[\s:-]+)?(?:\d[ \-]?){13}\d"
    r"|(?:\d[ \-]?){12}\d|(?:\d[ \-]?){11}\d|(?:\d[ \-]?){7}\d)"
    r"(?!\w)(?![-]\d)"
)


def _gtin_emit(span: tuple[int, int], ctx: ScanContext) -> GTINNotation:
    raw = ctx.text[span[0] : span[1]]
    rest = _GTIN_LABEL_RE.sub("", raw, count=1)
    ai_match = _GTIN_AI_RE.match(rest)
    if ai_match is not None:
        has_ai = True
        rest = rest[ai_match.end() :]
    else:
        has_ai = False
    digits = "".join(ch for ch in rest if ch in "0123456789")
    return GTINNotation(digits=digits, native_length=len(digits), has_ai=has_ai)


_GTIN_MATCHER = LabelMatcher(
    labels=_GTIN_LABELS,
    separator=r"[\s:-]+",
    glued_policy="reject",
    pattern=_GTIN_BODY,
    flags=re.IGNORECASE | re.ASCII,
    boundary=BoundarySpec.WORD,
    anchors=HasDigit().as_set(),
    emit=_gtin_emit,
)


class GTINRecognitionGrammar(PipelineGrammar[GTINNotation]):
    """GTIN recognition: 8/12/13/14-digit with labels and AI wrapper."""

    name = "gtin_recognition"
    semantics = "gtin_recognition"
    single_value = True
    pre = StandardPre[GTINNotation](empty_guard=True)
    matchers = (_GTIN_MATCHER,)


# Scaffolder seam: capability.py imports GTINRecognition; keep it an alias.
GTINRecognition = GTINRecognitionGrammar
