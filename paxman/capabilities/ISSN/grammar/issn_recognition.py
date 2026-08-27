"""ISSN recognition — label kind (ADR §9.7) with glued allow."""

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
    pattern=r"\d{4}-?\d{3}[0-9Xx]",
    flags=re.IGNORECASE,
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
