"""Scanner matcher — (context,pos)->(end,Notation)|None, non-overlapping advance."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from paxman.core.grammar.anchors import AnchorSet
from paxman.core.grammar.boundary_spec import BoundarySpec
from paxman.core.grammar.scan_context import View

ScanFn = Callable[[View, int], tuple[int, Any] | None]


@dataclass(frozen=True, slots=True)
class ScannerMatcher:
    scan: ScanFn
    view_name: str | None = None
    anchors: AnchorSet = field(default_factory=AnchorSet)
    boundary: BoundarySpec | None = None
    emit: Callable[[tuple[int, int], Any], Any] | None = None
    max_window: int = 2048

    def match(self, view: View) -> list[tuple[int, int]]:
        out: list[tuple[int, int]] = []
        s = view.subject
        pos = 0
        n = len(s)
        while pos < n:
            res = self.scan(view, pos)
            if res is not None:
                end, _notation = res
                # consuming-mode inner span only: if boundary is consuming,
                # emitted span is inner? For MVP emit pos->end; engine_loop
                # translates via view.original_span
                # Ensure advance includes delimiters if scanner consumed them?
                # For now just pos->end
                out.append((pos, end))
                pos = end if end > pos else pos + 1
            else:
                pos += 1
        return out
