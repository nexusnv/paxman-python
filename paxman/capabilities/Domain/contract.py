"""Domain contract — user-facing configuration."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import ClassVar

from paxman.core.capability_contract import CapabilityContract


@dataclass(frozen=True)
class DomainContract(CapabilityContract):
    """User-facing configuration for the Domain capability.

    The default ``ascii`` format renders the canonical A-label form:
    lowercase ASCII labels joined by dots, without a trailing dot — the
    DNS wire/protocol form (RFC 5890 §2.3.2.1).

    Offered formats (ADR-0011 classes): ``unicode`` — encoding. The
    rendering decodes each ``xn--`` label with the RFC 3492 Punycode
    codec to produce the U-label presentation of the SAME canonical
    entity; decode∘encode is the identity on validated labels, so the
    rendering re-enters the default contract onto the same canonical
    value (ADR-0010 re-entry holds).

    Non-default scope knobs (single-label acceptance, underscore
    selector labels) are deliberately not shipped: they arrive later
    only as gated features declared through ``requires_features`` on
    the rule that reads them, never as contract fields read by
    grammars.
    """

    DEFAULT_OUTPUT_FORMAT: ClassVar[str] = "ascii"
    OFFERED_OUTPUT_FORMATS: ClassVar[frozenset[str]] = frozenset({"unicode"})

    capability_name: str = field(default="domain", init=False)

    # Non-default knobs, each DECLARED as requires_features on the rules
    # that would read them (none shipped in v1 — comments only):
    #   allow_single_label: bool = False     # "localhost"/intranet scope
    #   allow_underscore:   bool = False     # DNS vs STD3 selector labels
    #   transitional:       bool = False     # PINNED False (ss would break W7)
    # suppress_common_words: inherited       # A0 exemption applies to words

    def __post_init__(self) -> None:
        super().__post_init__()
