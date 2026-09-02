"""ISSN recognition — label kind (ADR §9.7) with glued allow.

Shipped as ``LabelMatcher`` (single matcher, not ``RegexStage``):
- labels ``{"ISSN", "ISSN-L", "ISSN-H"}``
  (ISSN-L = Linking ISSN per ISO 3297:2022 §3.4.4,
  ISSN-H = History ISSN; lexical shape identical, semantic distinction deferred)
- separator ``[\\s:-]*`` with ``glued_policy="allow"`` — ``ISSN03178471`` glues,
  vs IBAN ``reject`` (``IBANDE89...`` → MISSING) per ADR §9.7 Table
- pattern ``\\d{4}-?\\d{3}[0-9Xx](?![-]\\d)`` — 8 chars, hyphen optional *only* at
  canonical position 4 (strict; ``1234 5679`` / ``1234 - 5679`` → MISSING per memo
  §13#5 Oracle fix 3), final char ``[0-9Xx]`` (``X``/``x`` folded to ``X``), trailing
  ``(?![-]\\d)`` blocks hyphen-digit continuation ``0317-8471-2`` truncated-match
  (WORD ``(?!\\w)`` alone would allow ``-`` then digit; ISBN B1 analogue)
- flags ``re.IGNORECASE|ASCII`` — label and ``x`` case-insensitive, ASCII digits only
- boundary ``BoundarySpec.WORD`` — blocks
  ``a0317-8471`` / ``_0317-8471`` / ``912345679``
  (9-digit run) / ``1234-5679a`` via ``(?<!\\w)`` / ``(?!\\w)``; punctuation
  ``(0317-8471)``, ``0317-8471.`` allowed
- hyphen-minus ``-`` only (U+002D); en/em dash ``\\u2013``/``\\u2014`` → MISSING per
  memo §13#7 (zotero strips ``[\\x2D\\xAD\\u2010-\\u2015]`` but we reject)
- ``urn:issn:0317-8471`` incidentally handled as ``issn:0317-8471`` via ISSN label
  (span (4,18) excludes ``urn:``; full URN grammar deferred per plan §6)
"""

import re

from paxman.capabilities.ISSN.notation import ISSNNotation
from paxman.core.grammar import BoundarySpec, PipelineGrammar, StandardPre
from paxman.core.grammar.anchors import HasDigit
from paxman.core.grammar.matchers.label import LabelMatcher
from paxman.core.grammar.scan_context import ScanContext


def _issn_emit(span: tuple[int, int], ctx: ScanContext) -> ISSNNotation:
    raw = ctx.text[span[0] : span[1]]
    digits = "".join(ch for ch in raw if ch in "0123456789Xx").upper()
    return ISSNNotation(digits=digits)


_ISSN_LABEL_MATCHER = LabelMatcher(
    labels=frozenset({"ISSN", "ISSN-L", "ISSN-H"}),
    separator=r"[\s:-]*",
    glued_policy="allow",
    pattern=r"\d{4}-?\d{3}[0-9Xx](?![-]\d)",
    flags=re.IGNORECASE | re.ASCII,
    boundary=BoundarySpec.WORD,
    anchors=HasDigit().as_set(),
    emit=_issn_emit,
)


class ISSNRecognitionGrammar(PipelineGrammar[ISSNNotation]):
    """ISSN recognition: 8-char identifier with optional label (glued allow)."""

    name = "issn_recognition"
    semantics = "issn_recognition"
    single_value = True
    pre = StandardPre[ISSNNotation](empty_guard=True)
    matchers = (_ISSN_LABEL_MATCHER,)
