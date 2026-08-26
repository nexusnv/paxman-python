"""URL notation types."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class URLNotation:
    """URL notation: a single URL string.

    Shape-only carrier (ADR §5): it stores the recognized text exactly as
    scanned and never validates it — validity is the rule layer's job (ADR §5).
    The single ``text`` component is the recognized URL string.
    """

    text: str
