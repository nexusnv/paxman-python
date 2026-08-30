"""Candidates matcher — enumerated formats / registry.

Thin wrapper over combinator ordered alt with per-candidate semantics
routing (strategy first|all). Date 4→1 is the first customer (ADR §9.6).

Frozen singletons (_DATE_CANDIDATES) store per-call routing in ContextVars
(_flat_ctx/_counts_ctx) for thread+asyncio isolation; _flat/_emit_counts kept
for introspection.
"""

from __future__ import annotations

import contextlib
import contextvars
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

# Context-local storage for per-call routing state. The matcher singletons
# (_DATE_CANDIDATES, etc.) are frozen module globals; storing flat/counts on
# `self` would race under concurrent canonicalize/scan. ContextVars give
# per-context (thread + asyncio task) isolation. Instance fields `_flat`
# / `_emit_counts` are kept for single-threaded test introspection via
# `getattr(matcher, "_flat")`.
_flat_ctx: Any = contextvars.ContextVar("_candidates_flat", default=None)
_counts_ctx: Any = contextvars.ContextVar("_candidates_counts", default=None)


def _tl_set_flat(matcher_id: int, flat: list[tuple[int, int, int]]) -> None:
    cur = _flat_ctx.get()
    m = dict(cur) if cur is not None else {}
    m[matcher_id] = flat
    _flat_ctx.set(m)
    cur_c = _counts_ctx.get()
    cm = dict(cur_c) if cur_c is not None else {}
    cm[matcher_id] = {}
    _counts_ctx.set(cm)


def _tl_get_flat(matcher_id: int) -> list[tuple[int, int, int]] | None:
    cur = _flat_ctx.get()
    if cur is None:
        return None
    return cur.get(matcher_id)


def _tl_get_counts(matcher_id: int) -> dict[tuple[int, int], int] | None:
    cur = _counts_ctx.get()
    if cur is None:
        return None
    return cur.get(matcher_id)


def _tl_set_counts(matcher_id: int, counts: dict[tuple[int, int], int]) -> None:
    cur = _counts_ctx.get()
    m = dict(cur) if cur is not None else {}
    m[matcher_id] = counts
    _counts_ctx.set(m)


def get_flat_for_matcher(matcher: Any) -> list[tuple[int, int, int]]:
    """Return current flat for a matcher — context-local first, else instance field."""
    fl = _tl_get_flat(id(matcher))
    if fl is not None:
        return fl
    return cast(list[tuple[int, int, int]], getattr(matcher, "_flat", []))


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
        _tl_set_flat(id(self), [])
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
        stored_flat: list[tuple[int, int, int]] = []
        if self.strategy == "first":
            # Dedup by (s, e) and boundary-filter compose: the boundary
            # verdict depends only on (s, e), so filtering the deduped
            # stream equals deduping the filtered stream (#68).
            seen: set[tuple[int, int]] = set()
            for s, e, idx in flat:
                key = (s, e)
                if key in seen:
                    continue
                if self.boundary is not None and not check_boundary(
                    view.subject, s, e, self.boundary
                ):
                    continue
                seen.add(key)
                result.append(key)
                stored_flat.append((s, e, idx))
        else:
            for s, e, idx in flat:
                if self.boundary is not None and not check_boundary(
                    view.subject, s, e, self.boundary
                ):
                    continue
                result.append((s, e))
                stored_flat.append((s, e, idx))
        # Update instance fields atomically for single-threaded introspection;
        # avoid clear()/extend() race on frozen singleton (4677ff9).
        with contextlib.suppress(AttributeError, TypeError, RuntimeError):
            object.__setattr__(self, "_flat", list(stored_flat))
        with contextlib.suppress(AttributeError, TypeError, RuntimeError):
            object.__setattr__(self, "_emit_counts", {})
        _tl_set_flat(id(self), stored_flat)
        return result

    def _emit_match(self, span: tuple[int, int], ctx: ScanContext) -> Any:
        flat = _tl_get_flat(id(self))
        if flat is None:
            flat = cast(list[tuple[int, int, int]], getattr(self, "_flat", []))
        counts = _tl_get_counts(id(self))
        if counts is None:
            counts = cast(dict[tuple[int, int], int], getattr(self, "_emit_counts", {}))
            _tl_set_counts(id(self), dict(counts))
            counts = _tl_get_counts(id(self)) or {}
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
        new_counts = dict(counts)
        new_counts[key] = cnt + 1
        _tl_set_counts(id(self), new_counts)
        try:
            inst_counts = getattr(self, "_emit_counts", None)
            if isinstance(inst_counts, dict):
                inst_counts[key] = cnt + 1
        except (AttributeError, TypeError, RuntimeError):
            pass
        cand = self.candidates[cand_idx]
        em = getattr(cand, "emit", None)
        if callable(em):
            return em(span, ctx)
        return span
