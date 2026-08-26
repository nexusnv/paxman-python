"""Absolute-URI recognition grammar for the URL capability (staged pipeline).

Recognizes absolute-URI/IRI spans (RFC 3986 section 4.2, RFC 3987 section
2.2) as scheme-anchored shape matches. Shape-only per ADR §5: validity is the
rule layer's job — the grammar never validates the scheme, host, or port,
and carries no scheme table.

The leading lookbehind (via BoundaryGuard.scheme_char()) rejects a scheme
preceded by a scheme-legal character. A PostStage applies the Appendix C
paren-balance trim and the ADR §9.3 bare-scheme drop (ADR-0008 S5) so the emitted
span is byte-identical to the legacy recognize().
"""

from __future__ import annotations

import re

from paxman.capabilities.URL.notation import URLNotation
from paxman.core.domain import RecognitionMatch
from paxman.core.grammar import (
    BoundaryGuard,
    PipelineGrammar,
    PostStage,
    RegexStage,
    StandardPre,
)

# Body: scheme anchor (ALPHA *( ALPHA / DIGIT / "+" / "-" / "." ) ":") then
# at least one URI/IRI body character (RFC 3986 section 2 + RFC 3987
# section 2.2 ucschar, plus tab/newline for Appendix C multi-line URIs),
# bounded by whitespace/control/delimiter characters on the right. The
# leading lookbehind is supplied by BoundaryGuard.scheme_char() (ADR-0008
# ADR-0009 §10) so no hard-coded lookaround literal remains in this file.
_URL_BODY = (
    r"[A-Za-z][A-Za-z0-9+.\-]*:"
    r'[^ <>"\x00-\x08\x0B\x0C\x0E-\x1F\x7F]*[^ <>"\x00-\x08\x0B\x0C\x0E-\x1F\x7F]'
)
_GUARD = BoundaryGuard.scheme_char()
_URL_PATTERN = _GUARD.lookbehind + _URL_BODY


def _url_notation(match: re.Match[str]) -> URLNotation:
    """Map a raw absolute-URI match to its verbatim-text notation."""
    return URLNotation(text=match.group(0))


def _url_trim(
    match: RecognitionMatch[URLNotation],
) -> RecognitionMatch[URLNotation] | None:
    """Appendix C paren-balance trim + ADR §9.3 bare-scheme drop.

    Drops trailing ")" only while it outnumbers "(" (counting once then
    trimming the run equals the legacy loop in one pass). After trimming,
    a span reduced to the bare scheme (no body past the colon) is dropped
    entirely (ADR §9.3) — it is not a valid absolute-URI match.
    """
    raw_span = match.raw_text
    excess = raw_span.count(")") - raw_span.count("(")
    trim = 0
    while trim < excess and raw_span[-(trim + 1)] == ")":
        trim += 1
    if trim:
        raw_span = raw_span[:-trim]
    scheme_end = raw_span.find(":")
    if len(raw_span) <= scheme_end + 1:
        return None
    return RecognitionMatch(
        notation=URLNotation(text=raw_span),
        start=match.start,
        end=match.start + len(raw_span),
        raw_text=raw_span,
    )


class AbsoluteUriRecognition(PipelineGrammar[URLNotation]):
    """Absolute-URI recognition: extracts scheme-anchored URI spans."""

    name = "absolute_uri_recognition"
    semantics = "absolute_uri_recognition"
    single_value = True

    pre = StandardPre[URLNotation](empty_guard=True)
    regex = RegexStage[URLNotation](pattern=_URL_PATTERN, notation_fn=_url_notation)
    post = PostStage[URLNotation](transform=_url_trim)
