"""Absolute-URI recognition grammar for the URL capability (ScannerMatcher).

Recognizes absolute-URI/IRI spans (RFC 3986 section 4.2, RFC 3987 section
2.2) as scheme-anchored shape matches. Shape-only per ADR §5: validity is the
rule layer's job — the grammar never validates the scheme, host, or port,
and carries no scheme table.

ScannerMatcher on the IDNAFold view (ADR-0009 §9.3, A4 offset maps): the
IDNA normalizer strips tab/newline/carriage-return with two-array offset
maps so the scanner rides the view's ``original_span`` discipline. The
scanner reproduces the legacy Appendix C paren-balance trim and ADR §9.3
bare-scheme drop that the retired PostStage applied, so emitted spans are
byte-identical to the legacy ``recognize()``.
"""

from __future__ import annotations

from paxman.capabilities.URL.notation import URLNotation
from paxman.core.grammar import BoundarySpec, ScannerMatcher, StandardPre
from paxman.core.grammar.pipeline import PipelineGrammar
from paxman.core.grammar.scan_context import ScanContext, View


def _is_forbidden(ch: str) -> bool:
    """Return True if ``ch`` is a URI delimiter / control per the legacy regex.

    Legacy pattern ``[ ^ <>"\\x00-\\x08\\x0B\\x0C\\x0E-\\x1F\\x7F]``
    forbids space, ``<``, ``>``, ``"``, and the control ranges
    ``\\x00-\\x08``, ``\\x0B``, ``\\x0C``, ``\\x0E-\\x1F``, ``\\x7F``.
    Tab (\\x09), LF (\\x0A) and CR (\\x0D) are *allowed* body chars — they
    are stripped by the IDNAFold view and therefore never appear in
    ``view.subject``, but their absence there still maps back to the original
    span via ``original_span``.
    """
    if ch in (" ", "<", ">", '"'):
        return True
    o = ord(ch)
    if 0x00 <= o <= 0x08:
        return True
    if o == 0x0B or o == 0x0C:
        return True
    if 0x0E <= o <= 0x1F:
        return True
    return o == 0x7F


def _url_scan(view: View, pos: int) -> tuple[int, URLNotation] | None:
    """Scanner function: (view, pos) -> (end, Notation) | None.

    Mirrors the legacy absolute-URI pattern plus trim in one
    pass on the IDNAFold view: scheme anchor, forbidden-delimiter-greedy
    body, paren-balance trim, bare-scheme drop.
    """
    subj = view.subject
    n = len(subj)
    if pos < 0 or pos >= n:
        return None
    ch0 = subj[pos]
    if not (ch0.isascii() and ch0.isalpha()):
        return None
    i = pos + 1
    while i < n:
        c = subj[i]
        if not (c.isascii() and (c.isalnum() or c in "+.-")):
            break
        i += 1
    if i >= n or subj[i] != ":":
        return None
    colon = i
    body_start = colon + 1
    if body_start >= n:
        return None
    if _is_forbidden(subj[body_start]):
        return None
    j = body_start
    while j < n and not _is_forbidden(subj[j]):
        j += 1
    raw_end = j
    slice_text = subj[pos:raw_end]
    excess = slice_text.count(")") - slice_text.count("(")
    trim = 0
    while trim < excess and slice_text[-(trim + 1)] == ")":
        trim += 1
    if trim:
        raw_end -= trim
    if raw_end - pos <= colon - pos + 1:
        return None
    return (raw_end, URLNotation(text=subj[pos:raw_end]))


def _url_emit(span: tuple[int, int], ctx: ScanContext) -> URLNotation:
    s, e = span
    raw = ctx.text[s:e]
    return URLNotation(text=raw)


_URL_SCANNER = ScannerMatcher(
    scan=_url_scan,
    view_name="idna",
    boundary=BoundarySpec.SCHEME_CHAR_LEFT,
    emit=_url_emit,
)


class AbsoluteUriRecognition(PipelineGrammar[URLNotation]):
    """Absolute-URI recognition: extracts scheme-anchored URI spans."""

    name = "absolute_uri_recognition"
    semantics = "absolute_uri_recognition"
    single_value = True

    pre = StandardPre[URLNotation](empty_guard=True)
    matchers = (_URL_SCANNER,)
