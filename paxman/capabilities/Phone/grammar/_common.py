"""Shared Phone grammar helpers — separator stripping.

Capability-local helper for Phone grammars (ADR-0009 §10 self-containment).
``paxman/core/grammar`` stays capability-agnostic (D2); Phone grammars share
this helper internally to avoid quadruplicated ``strip_separators`` and
translation-table construction.
"""

from __future__ import annotations

# Translation tables — built once, reused.
_SEPARATORS = str.maketrans("", "", " ().-")
_SEPARATORS_WITH_PLUS = str.maketrans("", "", "+ ().-")


def strip_separators(value: str, *, plus: bool = False) -> str:
    """Remove phone separators from a raw match.

    Args:
        value: Raw match text (digits, separators, optional leading "+").
        plus: Also strip a leading "+" (E.164 and tel-URI matches).

    Returns:
        The digit-only number.
    """
    if plus:
        return value.translate(_SEPARATORS_WITH_PLUS)
    return value.translate(_SEPARATORS)
