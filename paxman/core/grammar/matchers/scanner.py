"""Scanner matcher — (context,pos)->(end,Notation)|None, non-overlapping advance.

Per ADR-0009 §9.3: ``scan: (context, pos) -> (end, Notation) | None``. The
kernel's loop tries the scanner at each position, advances to ``end`` on hit,
``pos+1`` on miss (libphonenumber non-overlapping discipline). Bounds are
carried as data (``max_window``). No shipped grammar uses it on the kernel
path yet — URL paren-balance and Phone E.164 remain on ``PostStage`` until
their parity shards are green (ADR §9.3). This implementation enforces
``max_window``, ``boundary`` (including ``consuming`` inner-span only per
ADR §10), and ``requires_features`` via the engine loop; the matcher itself
only caps ``end`` to ``max_window`` and checks boundaries at hit positions.
"""

from __future__ import annotations

import hashlib
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

ScanFn = Callable[[View, int], tuple[int, Any] | None]


@dataclass(frozen=True, slots=True)
class ScannerMatcher:
    scan: ScanFn
    view_name: str | None = None
    anchors: AnchorSet = field(default_factory=AnchorSet)
    boundary: BoundarySpec | None = None
    emit: Callable[[tuple[int, int], Any], Any] | None = None
    max_window: int = 2048
    requires_features: frozenset[str] = field(default_factory=lambda: frozenset[str]())
    digest: str = field(init=False, repr=False, default="")

    def __post_init__(self) -> None:
        _validate_emit(self.emit, type(self).__name__)
        qualname = getattr(self.scan, "__qualname__", type(self.scan).__name__)
        boundary_repr = repr(self.boundary) if self.boundary is not None else "None"
        view_repr = self.view_name if self.view_name is not None else "None"
        digest_val = hashlib.sha256(
            f"{qualname}\x00{self.max_window}\x00{view_repr}\x00{boundary_repr}".encode()
        ).hexdigest()
        object.__setattr__(self, "digest", digest_val)

    def match(self, view: View) -> list[tuple[int, int]]:
        out: list[tuple[int, int]] = []
        s = view.subject
        pos = 0
        n = len(s)
        while pos < n:
            res = self.scan(view, pos)
            if res is not None:
                end, _notation = res
                # Guard against scanner contract violations
                if not isinstance(end, int) or end < pos or end > n:
                    # Clamp or advance by 1 on violation to avoid infinite loop
                    # Surface as no-match at this pos
                    pos += 1
                    continue
                # Enforce max_window — bounds as data (libphonenumber discipline).
                # Do not silently clamp to max_window; treat as miss and advance
                # to avoid infinite loop while preserving the bound.
                if end - pos > self.max_window:
                    pos += 1
                    continue
                # Boundary check at hit positions (O(hits), not O(positions))
                if self.boundary is not None and not check_boundary(
                    s, pos, end, self.boundary
                ):
                    pos += 1
                    continue
                # ADR §10 consuming-mode: emitted span is inner only. Scanners that
                # consume delimiters for advance must return inner end; if they
                # return the consuming span, engine_loop will not re-trim. For now
                # we emit pos->end as returned (inner).
                out.append((pos, end))
                pos = end if end > pos else pos + 1
            else:
                pos += 1
        return out
