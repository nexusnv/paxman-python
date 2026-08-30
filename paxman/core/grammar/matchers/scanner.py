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
    view: str | None = None
    anchors: AnchorSet = field(default_factory=AnchorSet)
    boundary: BoundarySpec | None = None
    emit: Callable[[tuple[int, int], Any], Any] | None = None
    max_window: int = 2048
    requires_features: frozenset[str] = field(default_factory=lambda: frozenset[str]())
    digest: str = field(init=False, repr=False, default="")

    def __post_init__(self) -> None:
        _validate_emit(self.emit, type(self).__name__)
        if (
            self.view is not None
            and self.view_name is not None
            and self.view != self.view_name
        ):
            raise ValueError(
                f"ScannerMatcher view/view_name mismatch: "
                f"{self.view!r} != {self.view_name!r}"
            )
        if self.view is not None and self.view_name is None:
            object.__setattr__(self, "view_name", self.view)
        elif self.view_name is not None and self.view is None:
            object.__setattr__(self, "view", self.view_name)
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
                # Boundary check at hit positions (O(hits), not O(positions)).
                # On a stripped view the subject's left/right char may not be
                # the original neighbor: if there's a gap between pos and
                # pos-1 or between end and end-1 in the original (a stripped
                # char), the original neighbor is that stripped char — the
                # engine re-checks the boundary on the original text for
                # stripped views, so the view-level check is deferred here.
                # Otherwise the view check is accurate (single-char guards;
                # multi-char guard windows spanning an older stripped char are
                # governed by the engine's original-text re-check).
                if self.boundary is not None:
                    left_gap = (
                        view.stripped_chars
                        and view.source_starts is not None
                        and view.source_ends is not None
                        and pos > 0
                        and view.source_starts[pos] != view.source_ends[pos - 1]
                    )
                    right_gap = (
                        view.stripped_chars
                        and view.source_starts is not None
                        and view.source_ends is not None
                        and end < n
                        and end > 0
                        and view.source_starts[end] != view.source_ends[end - 1]
                    )
                    if left_gap or right_gap:
                        # Gap → original neighbor is a stripped char, not
                        # forbidden, so boundary passes; no view check.
                        # Engine's original-text re-check governs.
                        pass
                    elif not check_boundary(s, pos, end, self.boundary):
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
