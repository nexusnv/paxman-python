"""RFC 5893 Bidi validation rule — the Bidi rule plus ContextJ controls.

Implements the RFC 5893 §2 six-condition Bidi rule: labels are typed by
their first character (L vs R/AL), and every label of a Bidi domain name
(a name with at least one R/AL/AN character, §1.4) must satisfy the
conditions for its type. Non-Bidi names pass unconditionally (§1.1
places no requirements on names without right-to-left characters).

Join controls (U+200C/U+200D) are rejected outright: they are
``deviation`` in the shipped table (kept by non-transitional mapping)
and their contextual allowance (RFC 5892 ContextJ) needs joining tables
that v1 does not ship — conservative reject.
"""

from __future__ import annotations

import unicodedata

from paxman.capabilities.Domain.idna_processing import finalize
from paxman.capabilities.Domain.notation import DomainNotation
from paxman.core.contract import Contract
from paxman.core.domain import Provenance, Rule, RuleStrategy

PUBLICATION = Provenance(
    authority="IETF",
    specification_name="RFC 5893",
    kind="specification",
    reference_url="https://www.rfc-editor.org/rfc/rfc5893",
    version="2010",
    lifecycle="active",
    publication_year=2010,
)

_RTL_CLASSES = frozenset({"R", "AL", "AN"})
_RTL_ALLOWED = frozenset({"R", "AL", "AN", "EN", "ES", "CS", "ET", "ON", "BN", "NSM"})
_LTR_ALLOWED = frozenset({"L", "EN", "ES", "CS", "ET", "ON", "BN", "NSM"})
_JOIN_CONTROLS = frozenset({"\u200c", "\u200d"})


def _strip_nsm_tail(label: str) -> str:
    """Remove trailing NSM characters (conditions 3/6 allow zero or more)."""
    core = label
    while core and unicodedata.bidirectional(core[-1]) == "NSM":
        core = core[:-1]
    return core


def bidi_ok(notation: DomainNotation) -> bool:
    """RFC 5893 §2 check with a non-Bidi fast path, plus ContextJ reject."""
    labels = notation.labels
    for label in labels:
        if _JOIN_CONTROLS & set(label):
            return False
    if not any(
        unicodedata.bidirectional(char) in _RTL_CLASSES
        for label in labels
        for char in label
    ):
        return True
    for label in labels:
        if not label:
            continue
        first = unicodedata.bidirectional(label[0])
        if first not in ("L", "R", "AL"):
            return False
        if first in ("R", "AL"):
            if any(
                unicodedata.bidirectional(char) not in _RTL_ALLOWED for char in label
            ):
                return False
            core = _strip_nsm_tail(label)
            if not core or unicodedata.bidirectional(core[-1]) not in (
                "R",
                "AL",
                "EN",
                "AN",
            ):
                return False
            classes = {unicodedata.bidirectional(char) for char in label}
            if "EN" in classes and "AN" in classes:
                return False
        else:
            if any(
                unicodedata.bidirectional(char) not in _LTR_ALLOWED for char in label
            ):
                return False
            core = _strip_nsm_tail(label)
            if not core or unicodedata.bidirectional(core[-1]) not in ("L", "EN"):
                return False
    return True


class Rfc5893BidiContext(Rule[DomainNotation]):
    """RFC 5893 Section 2 — the Bidi rule for IDNA labels, plus ContextJ."""

    name = "Section-2-bidi-context"
    strategy = RuleStrategy.PARSER
    provenance = PUBLICATION
    citation = "RFC 5893 §2 Bidi rule"
    target_semantics = frozenset({"ascii_hostname", "idn_hostname"})
    requires_features = frozenset()

    def matches(self, notation: DomainNotation, contract: Contract) -> bool:
        """Return True when the notation satisfies the Bidi rule."""
        return bidi_ok(notation)

    def normalize(self, notation: DomainNotation, contract: Contract) -> str:
        """Return the canonical A-label form shared by every rule."""
        return finalize(notation.labels)
