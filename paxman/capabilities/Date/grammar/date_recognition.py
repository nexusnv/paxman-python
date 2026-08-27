"""Date recognition — consolidated candidates (ADR §9.6).

Single grammar with four ordered candidates (iso8601, us, european, slash_iso)
using CandidatesMatcher strategy="all" to preserve AMBIGUOUS for 01/02/2026.
Per-candidate semantics routing is preserved via the shared
``date_calendar_date`` semantics plus rule affinity (all Date rules target
the new semantics). Iso and slash_iso share iso8601_calendar_date originally
but now coalesce under the single grammar; us/european remain distinct via
notation difference and cross-validation.
"""

from __future__ import annotations

import re

from paxman.capabilities.Date.notation import DateNotation
from paxman.core.grammar import BoundarySpec, PipelineGrammar, StandardPre
from paxman.core.grammar.anchors import AnchorSet, HasDigit
from paxman.core.grammar.matchers.candidates import CandidatesMatcher
from paxman.core.grammar.matchers.regex import RegexMatcher
from paxman.core.grammar.scan_context import ScanContext


def _iso_emit(span: tuple[int, int], ctx: ScanContext) -> DateNotation:
    raw = ctx.text[span[0] : span[1]]
    m = re.match(r"(\d{4})-(\d{2})-(\d{2})", raw)
    assert m is not None
    return DateNotation(N1=m.group(1), N2=m.group(2), N3=m.group(3))


def _slash_emit(span: tuple[int, int], ctx: ScanContext) -> DateNotation:
    raw = ctx.text[span[0] : span[1]]
    m = re.match(r"(\d{4})/(\d{1,2})/(\d{1,2})", raw)
    assert m is not None
    return DateNotation(N1=m.group(1), N2=m.group(2), N3=m.group(3))


def _slash_us_eu_emit(span: tuple[int, int], ctx: ScanContext) -> DateNotation:
    raw = ctx.text[span[0] : span[1]]
    m = re.match(r"(\d{1,2})/(\d{1,2})/(\d{4}|\d{2})", raw)
    assert m is not None
    return DateNotation(N1=m.group(1), N2=m.group(2), N3=m.group(3))


ISO_MATCHER = RegexMatcher(
    pattern=r"(\d{4})-(\d{2})-(\d{2})",
    boundary=BoundarySpec.DIGIT,
    view=None,
    anchors=HasDigit().as_set(),
    emit=_iso_emit,
)

SLASH_ISO_MATCHER = RegexMatcher(
    pattern=r"(\d{4})/(\d{1,2})/(\d{1,2})",
    boundary=BoundarySpec.DIGIT,
    view=None,
    anchors=HasDigit().as_set(),
    emit=_slash_emit,
)

US_MATCHER = RegexMatcher(
    pattern=r"(\d{1,2})/(\d{1,2})/(\d{4}|\d{2})",
    boundary=BoundarySpec.DIGIT,
    view=None,
    anchors=HasDigit().as_set(),
    emit=_slash_us_eu_emit,
)

EUROPEAN_MATCHER = RegexMatcher(
    pattern=r"(\d{1,2})/(\d{1,2})/(\d{4}|\d{2})",
    boundary=BoundarySpec.DIGIT,
    view=None,
    anchors=HasDigit().as_set(),
    emit=_slash_us_eu_emit,
)

_ISO_MATCHER = ISO_MATCHER
_SLASH_ISO_MATCHER = SLASH_ISO_MATCHER
_US_MATCHER = US_MATCHER
_EUROPEAN_MATCHER = EUROPEAN_MATCHER

_DATE_CANDIDATES = CandidatesMatcher(
    candidates=(ISO_MATCHER, US_MATCHER, EUROPEAN_MATCHER, SLASH_ISO_MATCHER),
    strategy="all",
    view_name=None,
    anchors=AnchorSet(),
    boundary=None,
    candidate_names=(
        "iso8601_recognition",
        "us_recognition",
        "european_recognition",
        "slash_iso_recognition",
    ),
    candidate_semantics=(
        "iso8601_calendar_date",
        "us_calendar_date",
        "european_calendar_date",
        "iso8601_calendar_date",
    ),
)


class DateGrammar(PipelineGrammar[DateNotation]):
    """Consolidated Date recognition — four candidates, strategy all."""

    name = "date_recognition"
    semantics = "date_calendar_date"
    single_value = True

    pre = StandardPre[DateNotation](empty_guard=True)
    matchers = (_DATE_CANDIDATES,)
