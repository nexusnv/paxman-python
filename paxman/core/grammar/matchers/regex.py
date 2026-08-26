"""Regex matcher — pure shape (ADR-0009 §9.1).

When the spec defines a syntactic shape — character classes, repetitions,
bounded separators. BIC, IBAN, ISBN/ISSN cores, IP v4, Date, Email standard,
Phone tel-URI/00. Contract: ``re.compile(pattern, flags).finditer(view.subject)``
with notation_fn, offset-translated at emit. Patterns carry bounds so worst-case
is linear. No backreferences.

This kind is declared for completeness (plan Task 7 module layout) and is
available for the ``BIC``/``Date`` candidates migration (Phase 3). No shipped
grammar uses it on the kernel path yet — legacy ``RegexStage`` remains the
shipped path until per-grammar parity shards are green.
"""

from __future__ import annotations

import hashlib
import re
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from paxman.core.grammar.anchors import AnchorSet
from paxman.core.grammar.boundary_spec import BoundarySpec, check_boundary
from paxman.core.grammar.matchers._emit_validation import (
    validate_emit as _validate_emit,
)
from paxman.core.grammar.scan_context import View

_check_boundary = check_boundary  # legacy alias for tests


@dataclass(frozen=True, slots=True)
class RegexMatcher:
    """Regex kind: bounded pattern finditer on a view."""

    pattern: str
    flags: int = 0
    boundary: BoundarySpec | None = None
    view: str | None = None
    anchors: AnchorSet = field(default_factory=AnchorSet)
    emit: Callable[[tuple[int, int], Any], Any] | None = None
    requires_features: frozenset[str] = field(default_factory=lambda: frozenset[str]())
    kind: str = field(default="regex", init=False)
    _compiled: re.Pattern[str] = field(init=False, repr=False)
    digest: str = field(init=False, repr=False, default="")

    def __post_init__(self) -> None:
        _validate_emit(self.emit, type(self).__name__)
        try:
            compiled = re.compile(self.pattern, self.flags)
        except re.error as exc:
            raise ValueError(f"Invalid regex pattern {self.pattern!r}: {exc}") from exc
        object.__setattr__(self, "_compiled", compiled)
        digest_val = hashlib.sha256(
            f"{self.pattern}\x00{self.flags}".encode()
        ).hexdigest()
        object.__setattr__(self, "digest", digest_val)

    def match(self, view: View) -> list[tuple[int, int]]:
        out: list[tuple[int, int]] = []
        for m in self._compiled.finditer(view.subject):
            s, e = m.start(), m.end()
            if self.boundary is not None and not check_boundary(
                view.subject, s, e, self.boundary
            ):
                continue
            out.append((s, e))
        return out
