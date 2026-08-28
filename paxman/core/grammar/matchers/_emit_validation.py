"""Emit arity validation — construction-time only (ADR-0009 §13 R3)."""

from __future__ import annotations

import inspect
from collections.abc import Callable
from typing import Any, cast


def validate_emit(emit: Any, matcher_name: str) -> None:
    """Validate that ``emit`` is a 2-param callable ``(span, context)``.

    Called once per matcher at construction (frozen singletons). Engine loop
    assumes validated and only keeps a cheap ``callable`` guard.
    """
    if emit is None:
        return
    if not callable(emit):
        raise TypeError(f"Matcher {matcher_name} has no callable emit")
    sig = inspect.signature(cast(Callable[..., Any], emit))
    if len(sig.parameters) != 2:
        raise TypeError(
            f"Matcher {matcher_name}.emit must have 2 params "
            f"(span, context), got {len(sig.parameters)}"
        )


# Back-compat alias — task expects `_validate_emit` name
_validate_emit = validate_emit
