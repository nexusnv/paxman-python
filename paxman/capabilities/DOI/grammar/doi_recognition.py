"""DOI recognition grammar — regex structural pattern matching."""

from __future__ import annotations

import re

from paxman.capabilities.DOI.notation import DOINotation
from paxman.core.grammar.boundary import BoundaryGuard
from paxman.core.grammar.pipeline import PipelineGrammar
from paxman.core.grammar.stages import RegexStage, StandardPre


def _ascii_lower(value: str) -> str:
    """Basic-Latin-only fold: U+0041-U+005A mapped to U+0061-U+007A.

    DOI Handbook Ch.3 'Case Insensitivity of the DOI Name'
    (PDF-confirmed): DOI names are equivalent iff their code point
    sequences are identical except U+0041..U+005A identical to
    U+0061..U+007A; no ISO/IEC 10646 normalization is performed.
    Full-Unicode ``str.lower()``/``casefold()`` would wrongly conflate
    e.g. U+00C1/U+00E1, which the Handbook declares NOT equivalent —
    so every other code point is preserved byte-identically.
    """
    return "".join(chr(ord(ch) + 32) if "A" <= ch <= "Z" else ch for ch in value)


# Registrant bound 4-9 digits per P1793/scholid/Gilmartin consensus; the
# bound doubles as the shortDOI policy (registrant too short never claims)
# and the over-long guard (10+ digits never claim). Dotted sub-registrant
# tail per Handbook §4.3.2 (e.g. hypothetical 10.500.100).
_DOI_PREFIX = r"10\.[0-9]{4,9}(?:\.[0-9]+)*"
# Suffix is quoteless non-space (Wikidata P8966 consensus: no whitespace,
# no '"'/'&'/'''), with the FINAL character additionally excluding sentence
# punctuation (VIII. trailing '.', ')', ',', ';', ':', '!', '?', ']') and
# '/' so spans exclude trailing damage while interior dots/slashes
# (10.7774/cevr.2016.5.1.19) are retained. A greedy quoteless \S+ with a
# trailing lookahead cannot express this (the greedy run would swallow the
# dot first); the constrained-final-char construction is the mechanism.
_DOI_SUFFIX = r"(?:(?![\"&'])\S)*(?:(?![\"&'.,;:!?)\]/])\S)"
# Label separator is [\s:-]+ one or more, never zero width: a glued
# "doi10.1038/..." must not fuse into a mention (ORCID precedent).
# Host tolerance mirrors Crossref display + Wikidata P8966: canonical
# https://doi.org/, legacy http://, deprecated-but-resolving dx. host,
# and the www. variant. URN/namespace carriers: urn:doi: (Handbook §4.4.3
# URN form, primary) and info:doi/ (info-uri registry era). The proxy
# URN-colon form (https://doi.org/urn:doi:10.123:456, Handbook §6.3.1)
# is DEFERRED: the colon is not mapped, so it never claims in v1.
_DOI_LABEL = r"(?:(?ai:DOI)[\s:-]+)?"
_DOI_HOST = r"(?:(?ai:https?://(?:dx\.|www\.)?doi\.org)/)?"
_DOI_INFO = r"(?:(?ai:info:doi)/)?"
_DOI_URN = r"(?:(?ai:urn:doi):)?"
_DOI_BODY = (
    rf"{_DOI_LABEL}{_DOI_HOST}{_DOI_INFO}{_DOI_URN}"
    rf"(?P<core>{_DOI_PREFIX}/{_DOI_SUFFIX})"
)
# word_only guards block left glue x10.1038/... and digit glue 110.1038/...
# (no 10. start survives the lookbehind). Right-side alphanumerics merge
# into the variable-width opaque suffix by construction (a longer DOI
# name), unlike fixed-width ORCID trailing guards.
_DOI_PATTERN = (
    BoundaryGuard.word_only().lookbehind
    + _DOI_BODY
    + BoundaryGuard.word_only().lookahead
)


def _doi_notation(match: re.Match[str]) -> DOINotation:
    core = match.group("core")
    prefix, _, suffix = core.partition("/")
    prefix, suffix = _ascii_lower(prefix), _ascii_lower(suffix)
    return DOINotation(prefix=prefix, suffix=suffix, canonical=f"{prefix}/{suffix}")


class DOIRecognitionGrammar(PipelineGrammar[DOINotation]):
    """DOI recognition — bare 10.-prefixed core with carrier groups.

    Bare name, case variants, resolver-URL (https/http/dx/www.),
    doi:/DOI: labels, urn:doi: and info:doi/ carriers.
    """

    name = "doi_recognition"
    semantics = "doi_recognition"
    single_value = True
    pre = StandardPre[DOINotation](empty_guard=True)
    regex = RegexStage[DOINotation](pattern=_DOI_PATTERN, notation_fn=_doi_notation)
