"""UNSPSC notation — grammar-normalized digit form."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class UNSPSCNotation:
    """UNSPSC notation — grammar-normalized digit form.

    ``digits`` is the 8-digit zero-padded code (a 6-digit class shorthand
    is padded +"00" by the grammar; a 10-digit input keeps its 8-digit
    stem here).
    ``level`` is one of "segment" | "family" | "class" | "commodity",
    derived from trailing-00 pairs (no authority lookup).
    ``function`` is the 2-digit business-function suffix, or "" when the
    input was 6/8 digits (trace-only, never affects validity).
    ``native_length`` is the spelled digit length (6, 8, or 10),
    retained as a facet for the ``native`` offered format.
    """

    digits: str
    level: str
    function: str
    native_length: int
