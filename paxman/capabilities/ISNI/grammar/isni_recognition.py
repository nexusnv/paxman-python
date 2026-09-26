"""ISNI recognition grammar — spaced display with compact/hyphen/URI carriers."""

from __future__ import annotations

import re

from paxman.capabilities.ISNI.notation import ISNINotation
from paxman.core.grammar.boundary import BoundaryGuard
from paxman.core.grammar.pipeline import PipelineGrammar
from paxman.core.grammar.stages import RegexStage, StandardPre

# Label separator is [\s:-]+ one or more, never zero width: a glued
# "ISNI0000 ..." must not fuse into a mention (BIC precedent).
# Host tolerance mirrors ecosystem practice: https://isni.org/isni/ (canonical),
# http://, www.isni.org/isni/. Carrier is the IANA-registered `urn:isni:` form.
# Payload is ASCII-only via inline (?ai:) — fullwidth digits never match;
# the i flag folds lowercase x into [X] before .upper() normalization.
# Canonical spaced quads are accepted alongside compact (bare 16-char) and
# hyphenated (ORCID-style input normalizes to spaced): separators are
# presentation, so every branch feeds the same spaced canonical (ADR-0010
# fixed-point requires re-recognizing each offered rendering).
# Single spaces only between quads — double spaces/tabs stay MISSING
# (bounded absorption, ISIN/LEI precedent).
_ISNI_LABEL = r"(?:(?ai:ISNI)[\s:-]+)?"
_ISNI_HOST = r"(?:(?ai:(?:https?://)?(?:www\.)?isni\.org/isni/))?"
_ISNI_CARRIER = r"(?:(?ai:urn:isni:))?"
_ISNI_GLUED_GUARD = r"(?!(?ai:ISNI[0-9]))"
# Trailing continuation guards are branch-local (ISBN truncated-continuation
# precedent): a fifth quad/group ("... 2683 1234", "...-2683-1") must not
# claim the first four, but a compact run followed by space+digit is a
# separate mention ("<16 digits> <16 digits>" → two mentions), so the
# compact branch carries no trailing guard.
# Continuation lookbehinds are branch-local: a spaced (hyphenated) payload
# starting right after `<digit><space>` (`<digit>-`) is the suffix window of
# a longer run ("0000 0000 0001 2103 2683"), never a fresh mention — finditer
# would otherwise restart inside the run and claim the valid suffix. The
# compact branch carries no such guard: "<16 digits> <16 digits>" is two
# separate mentions (word_only already blocks digit-glued starts).
_ISNI_SPACED = r"(?ai:\d{4}(?: \d{4}){2} \d{3}[\dX])(?![ ]\d)"
_ISNI_COMPACT = r"(?ai:\d{15}[\dX])"
_ISNI_HYPHEN = r"(?ai:\d{4}(?:-\d{4}){2}-\d{3}[\dX])(?![-]\d)"
_ISNI_BODY = (
    rf"{_ISNI_LABEL}{_ISNI_HOST}{_ISNI_CARRIER}{_ISNI_GLUED_GUARD}"
    rf"(?P<isni>(?<![\d] ){_ISNI_SPACED}|{_ISNI_COMPACT}|(?<![\d]-){_ISNI_HYPHEN})"
)
# word_only guards block left glue X0000... and right glue ...2683Y.
# The negative lookahead blocks glued label without separator.
_ISNI_PATTERN = (
    BoundaryGuard.word_only().lookbehind
    + _ISNI_BODY
    + BoundaryGuard.word_only().lookahead
)


def _isni_notation(match: re.Match[str]) -> ISNINotation:
    """Build an ISNI notation from a regex match."""
    raw = match.group("isni").upper()
    compact = "".join(ch for ch in raw if ch.isascii() and ch.isalnum())
    spaced = f"{compact[:4]} {compact[4:8]} {compact[8:12]} {compact[12:]}"
    group0 = match.group(0).lower()
    return ISNINotation(
        compact=compact,
        spaced=spaced,
        uri=f"https://isni.org/isni/{compact}",
        check=compact[-1],
        is_uri="true" if ("isni.org" in group0 or "urn:isni:" in group0) else "false",
    )


class ISNIRecognitionGrammar(PipelineGrammar[ISNINotation]):
    """ISNI recognition — spaced display 4-4-4-4 with compact, hyphenated,
    labeled, URI, and URN-carrier forms.
    """

    name = "isni_recognition"
    semantics = "isni_recognition"
    single_value = True
    pre = StandardPre[ISNINotation](empty_guard=True)
    regex = RegexStage[ISNINotation](pattern=_ISNI_PATTERN, notation_fn=_isni_notation)
