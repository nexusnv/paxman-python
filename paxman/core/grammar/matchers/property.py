"""Property matcher — generated sorted-range bisect (deferred)."""

from __future__ import annotations

import bisect
from dataclasses import dataclass, field
from typing import Any, cast

from paxman.core.grammar.anchors import AnchorSet
from paxman.core.grammar.boundary_spec import BoundarySpec
from paxman.core.grammar.scan_context import View


@dataclass(frozen=True, slots=True)
class PropertyMatcher:
    ranges: tuple[tuple[int, int], ...] = ()  # sorted (start, end) inclusive
    view_name: str | None = None
    anchors: AnchorSet = field(default_factory=AnchorSet)
    boundary: BoundarySpec | None = None

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
        return []
