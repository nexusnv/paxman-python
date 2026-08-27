"""Candidates matcher — enumerated formats / registry.

Thin wrapper over combinator ordered alt with per-candidate semantics
routing (strategy first|all). Date 4→1 is the first customer (ADR §9.6).
"""

from __future__ import annotations

import hashlib
import re
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any, Literal, cast

from paxman.core.grammar.anchors import AnchorSet
from paxman.core.grammar.boundary_spec import BoundarySpec, check_boundary
from paxman.core.grammar.matchers._emit_validation import (
    validate_emit as _validate_emit,
)
from paxman.core.grammar.scan_context import ScanContext, View


@dataclass(frozen=True, slots=True)
class CandidatesMatcher:
    candidates: tuple[Any, ...] = ()
    strategy: Literal["first", "all"] = "all"
    view_name: str | None = None
    view: str | None = None
    anchors: AnchorSet = field(default_factory=AnchorSet)
    boundary: BoundarySpec | None = None
    requires_features: frozenset[str] = field(default_factory=lambda: frozenset[str]())
    emit: Callable[[tuple[int, int], Any], Any] | None = field(default=None, repr=False)
    candidate_names: tuple[str, ...] = field(default_factory=tuple, repr=False)
    candidate_semantics: tuple[str, ...] = field(default_factory=tuple, repr=False)
    suppressible: bool = False
    kind: str = field(default="candidates", init=False)
    digest: str = field(init=False, repr=False, default="")
    _flat: list[tuple[int, int, int]] = field(
        default_factory=lambda: cast(list[tuple[int, int, int]], []),
        init=False,
        repr=False,
        hash=False,
        compare=False,
    )
    _emit_counts: dict[tuple[int, int], int] = field(
        default_factory=lambda: cast(dict[tuple[int, int], int], {}),
        init=False,
        repr=False,
        hash=False,
        compare=False,
    )

    def __post_init__(self) -> None:
        if self.view is not None and self.view_name is None:
            object.__setattr__(self, "view_name", self.view)
        elif self.view_name is not None and self.view is None:
            object.__setattr__(self, "view", self.view_name)
        # If no explicit emit, use per-candidate dispatch
        if self.emit is None:
            object.__setattr__(self, "emit", self._emit_match)
        _validate_emit(self.emit, type(self).__name__)
        cand_digests: list[str] = []
        for c in self.candidates:
            d = getattr(c, "digest", None)
            if isinstance(d, str) and d:
                cand_digests.append(d)
            else:
                try:
                    cand_digests.append(repr(c))
                except (
                    ValueError,
                    TypeError,
                    AttributeError,
                    RecursionError,
                    RuntimeError,
                ):
                    cand_digests.append(str(c))
        view_repr = (
            self.view_name
            if self.view_name is not None
            else (self.view if self.view is not None else "None")
        )
        boundary_repr = repr(self.boundary) if self.boundary is not None else "None"
        anchors_repr = repr(self.anchors)
        names_repr = "|".join(self.candidate_names) if self.candidate_names else ""
        sems_repr = (
            "|".join(self.candidate_semantics) if self.candidate_semantics else ""
        )
        digest_val = hashlib.sha256(
            f"{'|'.join(cand_digests)}\x00{self.strategy}\x00{view_repr}\x00{boundary_repr}\x00{anchors_repr}\x00{names_repr}\x00{sems_repr}".encode()
        ).hexdigest()
        object.__setattr__(self, "digest", digest_val)
        object.__setattr__(self, "_flat", [])
        object.__setattr__(self, "_emit_counts", {})

    def match(self, view: View) -> list[tuple[int, int]]:
        try:
            self._flat.clear()
        except (AttributeError, TypeError, RuntimeError):
            object.__setattr__(self, "_flat", [])
        try:
            self._emit_counts.clear()
        except (AttributeError, TypeError, RuntimeError):
            object.__setattr__(self, "_emit_counts", {})
        per_candidate_spans: list[list[tuple[int, int]]] = []
        for cand in self.candidates:
            try:
                cand_any: Any = cand
                spans_any: Any = cand_any.match(view)
                if isinstance(spans_any, list):
                    spans = cast(list[tuple[int, int]], spans_any)
                else:
                    spans = cast(list[tuple[int, int]], [])
            except (
                re.error,
                ValueError,
                TypeError,
                AttributeError,
                RuntimeError,
            ):
                spans = cast(list[tuple[int, int]], [])
            per_candidate_spans.append(spans)
        flat: list[tuple[int, int, int]] = []
        for idx, spans in enumerate(per_candidate_spans):
            for s, e in spans:
                if not isinstance(s, int) or not isinstance(e, int):
                    continue
                flat.append((s, e, idx))
        flat.sort(key=lambda x: (x[0], x[1], x[2]))
        result: list[tuple[int, int]] = []
        if self.strategy == "first":
            seen: set[tuple[int, int]] = set()
            for s, e, _ in flat:
                key = (s, e)
                if key not in seen:
                    seen.add(key)
                    result.append((s, e))
        else:
            for s, e, _ in flat:
                result.append((s, e))
        if self.boundary is not None:
            filtered: list[tuple[int, int]] = []
            for s, e in result:
                if check_boundary(view.subject, s, e, self.boundary):
                    filtered.append((s, e))
            result = filtered
        if self.strategy == "first":
            seen2: set[tuple[int, int]] = set()
            stored_flat: list[tuple[int, int, int]] = []
            for s, e, idx in flat:
                if (s, e) not in seen2:
                    if self.boundary is not None and not check_boundary(
                        view.subject, s, e, self.boundary
                    ):
                        continue
                    seen2.add((s, e))
                    stored_flat.append((s, e, idx))
        else:
            stored_flat = []
            for s, e, idx in flat:
                if self.boundary is not None and not check_boundary(
                    view.subject, s, e, self.boundary
                ):
                    continue
                stored_flat.append((s, e, idx))
        try:
            self._flat.clear()
            self._flat.extend(stored_flat)
        except (AttributeError, TypeError, ValueError, RuntimeError):
            object.__setattr__(self, "_flat", stored_flat)
        try:
            self._emit_counts.clear()
        except (AttributeError, TypeError, RuntimeError):
            object.__setattr__(self, "_emit_counts", {})
        return result

    def _emit_match(self, span: tuple[int, int], ctx: ScanContext) -> Any:
        flat: list[tuple[int, int, int]] = getattr(self, "_flat", [])
        counts: dict[tuple[int, int], int] = getattr(self, "_emit_counts", {})
        key = (span[0], span[1])
        occ: list[int] = [idx for s, e, idx in flat if s == span[0] and e == span[1]]
        if not occ:
            if self.candidates:
                cand = self.candidates[0]
                em = getattr(cand, "emit", None)
                if callable(em):
                    return em(span, ctx)
            return span
        cnt = counts.get(key, 0)
        if cnt >= len(occ):
            cnt = len(occ) - 1
        cand_idx = occ[cnt]
        counts[key] = cnt + 1
        cand = self.candidates[cand_idx]
        em = getattr(cand, "emit", None)
        if callable(em):
            return em(span, ctx)
        return span
