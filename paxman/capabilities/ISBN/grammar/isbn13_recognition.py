"""ISBN-13 recognition grammar (staged pipeline).

Recognizes 13-digit ISBNs with optional label and separators. The hyphen/space
tolerance is regex-native (the lookahead extracts the digit run via a
backreference). The trailing word boundary ``\\b`` handles the right edge; no
additional trailing guard is needed (the previous ``isbn_trail`` lookbehind was
inert after the final digit).
"""

from __future__ import annotations

import re

from paxman.capabilities.ISBN.notation import ISBNNotation
from paxman.core.grammar import PipelineGrammar, RegexStage, StandardPre

_ISBN13_BODY = r"\b(?:ISBN(?:-13)?[\s:-]+)?(?=((?:\d[ -]?){12}\d)(?![\d]))\1"
# Trailing (?![-]\d) mirrors ISBN-10 fix: reject hyphen+digit continuation that
# would indicate a truncated 13-digit prefix (e.g. "1-9780306406157" handling).
# Plain (?![\d]) only blocks immediate digit; \b still handles word boundaries.
_ISBN13_PATTERN = _ISBN13_BODY + r"(?![-]\d)\b"


def _isbn13_notation(match: re.Match[str]) -> ISBNNotation:
    """Map an ISBN-13 match to its digit-string notation."""
    digits = "".join(ch for ch in match.group(1) if ch in "0123456789")
    return ISBNNotation(shape="isbn13", digits=digits)


class ISBN13RecognitionGrammar(PipelineGrammar[ISBNNotation]):
    """ISBN-13 recognition: 13-digit ISBN with optional label and separators."""

    name = "isbn13_recognition"
    semantics = "isbn13_recognition"
    single_value = True

    pre = StandardPre[ISBNNotation](empty_guard=True)
    regex = RegexStage[ISBNNotation](
        pattern=_ISBN13_PATTERN, notation_fn=_isbn13_notation, flags=re.IGNORECASE
    )
