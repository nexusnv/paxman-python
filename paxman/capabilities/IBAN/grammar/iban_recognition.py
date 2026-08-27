"""IBAN recognition — label kind (ADR §9.7) with glued reject."""

from __future__ import annotations

import re as _re

from paxman.capabilities.IBAN.notation import IBANNotation
from paxman.core.grammar import BoundarySpec, PipelineGrammar, StandardPre
from paxman.core.grammar.matchers.label import LabelMatcher
from paxman.core.grammar.scan_context import ScanContext


def _iban_emit(span: tuple[int, int], ctx: ScanContext) -> IBANNotation:
    raw = ctx.text[span[0] : span[1]]
    m = _re.search(_IBAN_CORE, raw)
    raw_compact = m.group(0) if m is not None else raw
    compact = "".join(ch for ch in raw_compact if ch.isalnum()).upper()
    country_code = compact[0:2]
    check_digits = compact[2:4]
    bban = compact[4:]
    return IBANNotation(
        country_code=country_code, check_digits=check_digits, bban=bban, compact=compact
    )


_IBAN_CORE = (
    r"(?ai:(?:[A-Z]{2}[0-9]{2}[A-Z0-9]{11,30}"
    r"|[A-Z]{2}[0-9]{2}(?: [A-Z0-9]{4}){2,7}(?: [A-Z0-9]{1,4})?))"
)

_IBAN_LABEL_MATCHER = LabelMatcher(
    labels=frozenset({"IBAN"}),
    separator=r"[\s:-]+",
    glued_policy="reject",
    pattern=_IBAN_CORE,
    flags=0,
    boundary=BoundarySpec.WORD,
    emit=_iban_emit,
)


class IBANRecognitionGrammar(PipelineGrammar[IBANNotation]):
    """IBAN recognition — CCDD+BBAN with optional IBAN label (glued reject)."""

    name = "iban_recognition"
    semantics = "iban_recognition"
    single_value = True
    pre = StandardPre[IBANNotation](empty_guard=True)
    matchers = (_IBAN_LABEL_MATCHER,)
