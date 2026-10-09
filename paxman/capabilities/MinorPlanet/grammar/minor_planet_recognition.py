"""Minor-planet recognition grammar (kernel RegexMatcher).

Single ``minor_planet_recognition`` grammar with lane alternation:
unpacked provisional (plus retrospective ``A8xx``/``A9xx`` and ``A/``
1-2-letter lanes, underscore separator), packed 7-char (case-sensitive),
extended ``_`` base-62 (case-sensitive), survey unpacked + packed,
parenthesized numbers, and packed numbers. Syntax only — case/space
normalization and lane dispatch; decode coherence lives in rules
(`rules/mpc_codec.py`), never imported here.
"""

from __future__ import annotations

import re

from paxman.capabilities.MinorPlanet.notation import MinorPlanetNotation
from paxman.core.grammar import (
    AnchorSet,
    BoundarySpec,
    PipelineGrammar,
    StandardPre,
)
from paxman.core.grammar.matchers.regex import RegexMatcher
from paxman.core.grammar.scan_context import ScanContext

# No re.IGNORECASE: unpacked lanes fold case explicitly ([A-Za-z] +
# .upper()), packed lanes are case-SIGNIFICANT (a0017 vs A0345).
_YEAR = r"(?:A[89]\d{2}|19\d{2}|20\d{2})"
_UNPACKED = (
    r"(?P<year>" + _YEAR + r")[ _]"
    r"(?P<hm>[A-Za-z])(?P<second>[A-Za-z])(?P<cycle>\d*)"
)
_APREFIX = (
    r"A/(?P<ayear>" + _YEAR + r")[ _]"
    r"(?P<ahm>[A-Za-z])(?P<asecond>[A-Za-z])?(?P<acycle>\d*)"
)
_SURVEY = r"(?P<surveynum>[1-9]\d{0,3})[ _](?P<survey>[Pp]-[Ll]|[Tt]-[123])"
_PACKED7 = r"(?P<packed7>[IJK]\d{2}[A-Z][0-9A-Za-z]\d[A-Z])"
_EXTENDED = r"(?P<extended>_[0-9A-Za-z][A-Z][0-9A-Za-z]{4})"
_SURVEYPACKED = r"(?P<surveypacked>(?:PLS|T[123]S)\d{3,4})"
# Bare `\d{5}` must not carve a 5-digit prefix out of an over-long year
# (`19955 XA`): refuse the digit lane when a separator + letter follows.
_PACKEDNUM = r"(?P<packednum>(?:\d{5}(?![ _][A-Za-z])|[A-Za-z]\d{4}|~[0-9A-Za-z]{4}))"
_NUMBER = r"\((?P<number>\d{1,8})\)"
_MP_BODY = (
    _APREFIX
    + r"|"
    + _UNPACKED
    + r"|"
    + _SURVEY
    + r"|"
    + _PACKED7
    + r"|"
    + _EXTENDED
    + r"|"
    + _SURVEYPACKED
    + r"|"
    + _PACKEDNUM
    + r"|"
    + _NUMBER
)
# Kernel spelling: BoundarySpec.WORD owns word edges; the trailing
# (?![-]\d) stays inline (ISBN-13/UNSPSC precedent: no hyphen-digit carve).
_MP_PATTERN = r"(?:" + _MP_BODY + r")(?![-]\d)"
_LANE_RE = re.compile(r"^(?:" + _MP_BODY + r")$", re.ASCII)


def _emit(span: tuple[int, int], ctx: ScanContext) -> MinorPlanetNotation:
    """Map a matched span to its lane-dispatched notation."""
    raw = ctx.text[span[0] : span[1]]
    m = _LANE_RE.match(raw)
    if m is None:  # pragma: no cover — matcher already matched this span
        return MinorPlanetNotation(designation=raw, form="provisional", packed="")
    if m.group("ayear") is not None:
        designation = (
            f"A/{m.group('ayear')} "
            f"{m.group('ahm')}{m.group('asecond') or ''}{m.group('acycle')}"
        ).upper()
        return MinorPlanetNotation(
            designation=designation, form="provisional", packed=""
        )
    if m.group("year") is not None:
        designation = (
            f"{m.group('year')} {m.group('hm')}{m.group('second')}{m.group('cycle')}"
        ).upper()
        return MinorPlanetNotation(
            designation=designation, form="provisional", packed=""
        )
    if m.group("surveynum") is not None:
        designation = f"{int(m.group('surveynum'))} {m.group('survey').upper()}"
        return MinorPlanetNotation(designation=designation, form="survey", packed="")
    if m.group("packed7") is not None:
        return MinorPlanetNotation(
            designation=m.group("packed7"), form="packed", packed=m.group("packed7")
        )
    if m.group("extended") is not None:
        return MinorPlanetNotation(
            designation=m.group("extended"),
            form="extended",
            packed=m.group("extended"),
        )
    if m.group("surveypacked") is not None:
        return MinorPlanetNotation(
            designation=m.group("surveypacked"),
            form="survey_packed",
            packed=m.group("surveypacked"),
        )
    if m.group("packednum") is not None:
        return MinorPlanetNotation(
            designation=m.group("packednum"),
            form="packed_number",
            packed=m.group("packednum"),
        )
    return MinorPlanetNotation(designation=m.group(0), form="number", packed="")


_MATCHER = RegexMatcher(
    pattern=_MP_PATTERN,
    flags=re.ASCII,
    boundary=BoundarySpec.WORD,
    view=None,
    anchors=AnchorSet(),
    emit=_emit,
)


class MinorPlanetRecognitionGrammar(PipelineGrammar[MinorPlanetNotation]):
    """Minor-planet recognition: unpacked/packed/survey/number lanes."""

    name = "minor_planet_recognition"
    semantics = "minor_planet_recognition"
    single_value = True

    pre = StandardPre[MinorPlanetNotation](empty_guard=True)
    matchers = (_MATCHER,)
