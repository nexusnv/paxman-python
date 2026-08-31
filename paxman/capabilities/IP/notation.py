"""IP notation types."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class IPNotation:
    """IP address notation — a single address string.

    Attributes:
        address: Raw matched address text (not normalized). Produced by
            grammars, consumed by rules which return the RFC 5952 / RFC 791
            canonical form via ``Candidate.value``.
    """

    address: str
