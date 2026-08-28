"""Verbatim legacy ISSN/IBAN grammars (pre-LabelMatcher migration).

Snapshot of the RegexStage PipelineGrammar logic at the start of
Label migration (commit 320d288), used by the Migration Proof
Harness to assert byte-identical RecognitionMatch output after
the label migration. Classes are renamed ``Legacy*`` to avoid
colliding with the migrated grammar classes.

Do NOT edit by hand — this is a frozen reference.
"""

from __future__ import annotations

import re

from paxman.capabilities.IBAN.notation import IBANNotation
from paxman.capabilities.ISSN.notation import ISSNNotation
from paxman.core.grammar.boundary import BoundaryGuard
from paxman.core.grammar.pipeline import PipelineGrammar
from paxman.core.grammar.stages import RegexStage, StandardPre

_ISSN_BODY = r"(?:ISSN(?:-L|-H)?[\s:-]*)?(?P<body>\d{4}-?\d{3}[0-9Xx])"
_ISSN_PATTERN: str = (
    BoundaryGuard.word_only().lookbehind
    + _ISSN_BODY
    + BoundaryGuard.digit().lookahead
    + r"\b"
)


def _issn_notation(match: re.Match[str]) -> ISSNNotation:
    raw_body = match.group("body")
    digits = "".join(ch for ch in raw_body if ch in "0123456789Xx").upper()
    return ISSNNotation(digits=digits)


class LegacyISSNRecognitionGrammar(PipelineGrammar[ISSNNotation]):
    """Legacy ISSN recognition — RegexStage with glued allow."""

    name = "issn_recognition"
    semantics = "issn_recognition"
    single_value = True
    pre = StandardPre[ISSNNotation](empty_guard=True)
    regex = RegexStage[ISSNNotation](
        pattern=_ISSN_PATTERN, notation_fn=_issn_notation, flags=re.IGNORECASE
    )


_IBAN_CORE = (
    r"(?ai:(?:[A-Z]{2}[0-9]{2}[A-Z0-9]{11,30}"
    r"|[A-Z]{2}[0-9]{2}(?: [A-Z0-9]{4}){2,7}(?: [A-Z0-9]{1,4})?))"
)
_IBAN_BODY = r"(?:IBAN[\s:-]+)?(?P<body>" + _IBAN_CORE + r")"
_IBAN_PATTERN: str = (
    BoundaryGuard.word_only().lookbehind
    + _IBAN_BODY
    + BoundaryGuard.word_only().lookahead
)


def _iban_notation(match: re.Match[str]) -> IBANNotation:
    raw = match.group("body")
    m = re.search(_IBAN_CORE, raw)
    raw_compact = m.group(0) if m is not None else raw
    compact = "".join(ch for ch in raw_compact if ch.isalnum()).upper()
    country_code = compact[0:2]
    check_digits = compact[2:4]
    bban = compact[4:]
    return IBANNotation(
        country_code=country_code, check_digits=check_digits, bban=bban, compact=compact
    )


class LegacyIBANRecognitionGrammar(PipelineGrammar[IBANNotation]):
    """Legacy IBAN recognition — RegexStage with glued reject."""

    name = "iban_recognition"
    semantics = "iban_recognition"
    single_value = True
    pre = StandardPre[IBANNotation](empty_guard=True)
    regex = RegexStage[IBANNotation](
        pattern=_IBAN_PATTERN, notation_fn=_iban_notation, flags=re.IGNORECASE
    )
