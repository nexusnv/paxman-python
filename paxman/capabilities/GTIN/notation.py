"""GTIN notation — grammar-normalized digit form."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class GTINNotation:
    """GTIN notation — grammar-normalized digit form.

    ``digits`` is the spelled digit string with separators, labels, and
    AI markers stripped (length 8/12/13/14, ASCII digits only).
    ``native_length`` is the spelled length (``== len(digits)``), retained
    as a facet for the ``native`` offered format.
    ``has_ai`` records whether an ``(01)``/``AI 01`` marker was present
    (trace-only, never affects validity).
    """

    digits: str
    native_length: int
    has_ai: bool
