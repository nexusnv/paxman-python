"""Property matcher — generated sorted-range bisect.

Implemented per ADR-0009 §9.5: membership is ``bisect`` on generated sorted-range
tuples (ICU ``UnicodeSet`` discipline; no ``\\p{...}``, no ``regex`` dep). The
kind is live but has no shipped data until the Unicode property snapshot is
materialized — ``paxman/core/grammar/data/unicode_ranges.py`` is currently
``UNICODE_RANGES = ()`` (see plan Task 11). When populated, this matcher finds
maximal contiguous runs where every code point satisfies the property.
"""

from __future__ import annotations

import bisect
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any, cast

from paxman.core.grammar.anchors import AnchorSet
from paxman.core.grammar.boundary_spec import BoundarySpec, check_boundary
from paxman.core.grammar.scan_context import View

_check_boundary = check_boundary  # legacy alias for tests


def _default_emit_property(span: tuple[int, int], _ctx: Any) -> tuple[int, int]:
    return span


@dataclass(frozen=True, slots=True)
class PropertyMatcher:
    ranges: tuple[tuple[int, int], ...] = ()  # sorted (start, end) inclusive
    view: str | None = None
    view_name: str | None = None  # deprecated alias for `view`; prefer `view`
    anchors: AnchorSet = field(default_factory=AnchorSet)
    boundary: BoundarySpec | None = None
    requires_features: frozenset[str] = field(default_factory=lambda: frozenset[str]())
    emit: Callable[[tuple[int, int], Any], Any] = field(default=_default_emit_property)
    kind: str = field(default="property", init=False)
    _chosen: str = field(default="", init=False, repr=False)

    def __post_init__(self) -> None:
        # Compat: `view_name` is deprecated alias for `view`. Keep both in sync
        # so engine_loop (which reads `view`) and legacy tests (which read
        # `view_name`) both see the value.
        if self.view is not None and self.view_name is None:
            object.__setattr__(self, "view_name", self.view)
        elif self.view_name is not None and self.view is None:
            object.__setattr__(self, "view", self.view_name)

    def _contains(self, cp: int) -> bool:
        idx = (
            bisect.bisect_right(cast(Any, self.ranges), cast(Any, (cp, float("inf"))))
            - 1
        )
        if idx < 0:
            return False
        s, e = self.ranges[idx]
        return s <= cp <= e

    def match(self, view: View) -> list[tuple[int, int]]:
        if not self.ranges:
            return []
        out: list[tuple[int, int]] = []
        subj = view.subject
        n = len(subj)
        i = 0
        while i < n:
            cp = ord(subj[i])
            if not self._contains(cp):
                i += 1
                continue
            # Start of a run
            start = i
            i += 1
            while i < n and self._contains(ord(subj[i])):
                i += 1
            end = i
            if self.boundary is not None and not check_boundary(
                subj, start, end, self.boundary
            ):
                continue
            out.append((start, end))
        return out
