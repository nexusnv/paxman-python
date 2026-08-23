"""ORCID recognition grammar — regex structural pattern matching."""

from __future__ import annotations

import re

from paxman.capabilities.ORCID.notation import ORCIDNotation
from paxman.core.grammar.boundary import BoundaryGuard
from paxman.core.grammar.pipeline import PipelineGrammar
from paxman.core.grammar.stages import RegexStage, StandardPre

# Label separator is [\s:-]+ one or more, never zero width: a glued
# "ORCID0000-..." must not fuse into a mention (BIC precedent).
# Host tolerance mirrors ORCID XSD orcid-uri plus ecosystem practice:
# https://orcid.org/ (canonical v2.1), http:// (v2.0 legacy),
# orcid.org/, www.orcid.org/.
# Payload is ASCII-only via inline (?ai:) — fullwidth digits never match;
# the i flag folds lowercase x into [X] before .upper() normalization.
_ORCID_LABEL = r"(?:(?ai:ORCID|ISNI)[\s:-]+)?"
_ORCID_HOST = r"(?:(?ai:(?:https?://)?(?:www\.)?orcid\.org)/)?"
_ORCID_GLUED_GUARD = r"(?!(?ai:(?:ORCID|ISNI)[0-9]))"
_ORCID_BODY = (
    rf"{_ORCID_LABEL}{_ORCID_HOST}{_ORCID_GLUED_GUARD}"
    r"(?P<hyphenated>(?ai:\d{4}-\d{4}-\d{4}-\d{3}[\dX]))"
)
# word_only guards block left glue X0000-... and right glue ...0097Y.
# The negative lookahead blocks glued label without separator.
_ORCID_PATTERN = (
    BoundaryGuard.word_only().lookbehind
    + _ORCID_BODY
    + BoundaryGuard.word_only().lookahead
)


def _orcid_notation(match: re.Match[str]) -> ORCIDNotation:
    hyphenated = match.group("hyphenated").upper()
    compact = hyphenated.replace("-", "")
    return ORCIDNotation(
        compact=compact,
        hyphenated=hyphenated,
        uri=f"https://orcid.org/{hyphenated}",
        check=compact[-1],
        is_uri="true" if "orcid.org" in match.group(0).lower() else "false",
    )


class ORCIDRecognitionGrammar(PipelineGrammar[ORCIDNotation]):
    """ORCID recognition — hyphenated 4-4-4-4 with optional label and URI host."""

    name = "orcid_recognition"
    semantics = "orcid_recognition"
    single_value = True
    pre = StandardPre[ORCIDNotation](empty_guard=True)
    regex = RegexStage[ORCIDNotation](
        pattern=_ORCID_PATTERN, notation_fn=_orcid_notation
    )


# Alias for scaffold capability import.
ORCIDRecognition = ORCIDRecognitionGrammar
