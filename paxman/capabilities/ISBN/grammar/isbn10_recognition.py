"""ISBN-10 recognition grammar (staged pipeline).

Recognizes 10-digit ISBNs with optional label and separators. The leading
digit-glued guard is supplied by BoundaryGuard.isbn10_lead() (ADR-0009 §10) so
no hard-coded lookaround literal remains in this file. The trailing boundary is
handled by ``\\b`` (the previous ``isbn_trail`` lookbehind after the final digit
was inert). The hyphen/space tolerance is regex-native (the lookahead extracts
the digit run via a backreference).
"""

from __future__ import annotations

import re

from paxman.capabilities.ISBN.notation import ISBNNotation
from paxman.core.grammar import BoundaryGuard, PipelineGrammar, RegexStage, StandardPre

_LEAD = BoundaryGuard.isbn10_lead()
_ISBN10_PATTERN = (
    _LEAD.lookbehind
    + r"(?:ISBN(?:-10)?[\s:-]+)?(?=((?:\d[ -]?){9}[0-9Xx])(?![\d]))\1"
    + r"\b"
)


def _isbn10_notation(match: re.Match[str]) -> ISBNNotation:
    """Map an ISBN-10 match to its digit-string notation (X uppercased)."""
    digits = "".join(ch for ch in match.group(1) if ch in "0123456789Xx").upper()
    return ISBNNotation(shape="isbn10", digits=digits)


class ISBN10RecognitionGrammar(PipelineGrammar[ISBNNotation]):
    """ISBN-10 recognition: 10-digit ISBN with optional label and separators."""

    name = "isbn10_recognition"
    semantics = "isbn10_recognition"
    single_value = True

    pre = StandardPre[ISBNNotation](empty_guard=True)
    regex = RegexStage[ISBNNotation](
        pattern=_ISBN10_PATTERN, notation_fn=_isbn10_notation, flags=re.IGNORECASE
    )
