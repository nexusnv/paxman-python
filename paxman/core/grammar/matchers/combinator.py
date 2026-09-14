"""Combinator matcher — seq/alt/opt/rep/label over child specs.

Minimal expr tree evaluated left-to-right with span capture (nom/winnow IResult
model). Ordered choice deterministic-first-branch-wins per ADR §9.4.
Scope frozen to 5 forms: seq/alt/opt/rep/label — no new forms.
"""

from __future__ import annotations

import hashlib
import re
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any, cast

from paxman.core.grammar.anchors import AnchorSet
from paxman.core.grammar.boundary_spec import BoundarySpec, check_boundary
from paxman.core.grammar.matchers._emit_validation import (
    validate_emit as _validate_emit,
)
from paxman.core.grammar.scan_context import View


def _collect_leaves(expr: Any, out: list[Any]) -> None:
    if isinstance(expr, tuple):
        t = cast(tuple[Any, ...], expr)
        if (
            len(t) >= 1
            and isinstance(t[0], str)
            and t[0] in ("seq", "alt", "opt", "rep", "label")
        ):
            kind = cast(str, t[0])
            if kind == "seq" or kind == "alt":
                children: Any = t[1] if len(t) > 1 else cast(list[Any], [])
                if isinstance(children, (list, tuple)):
                    for ch in cast(Any, children):
                        _collect_leaves(ch, out)
                return
            if kind == "opt":
                child = t[1] if len(t) > 1 else None
                if child is not None:
                    _collect_leaves(child, out)
                return
            if kind == "rep":
                child = t[1] if len(t) > 1 else None
                if child is not None:
                    _collect_leaves(child, out)
                return
            if kind == "label":
                child2: Any = t[2] if len(t) > 2 else (t[1] if len(t) > 1 else None)
                if child2 is not None:
                    _collect_leaves(child2, out)
                return
    if hasattr(cast(Any, expr), "match"):
        attr = getattr(cast(Any, expr), "match", None)
        if callable(attr):
            out.append(expr)


_SEQ_EVAL_BUDGET = 10000  # hard cap on seq-branch attempts per start (#73 L3)


def _eval_ends(
    expr: Any,
    view: View,
    pos: int,
    leaf_maps: dict[int, dict[int, list[int]]],
    budget: list[int],
) -> list[int]:
    """All possible end positions of ``expr`` at ``pos``, longest-first.

    Leaf alternatives branch (every end at ``pos`` is explored); ``seq``
    enumerates every child-end combination level by level and returns them
    longest-first, so a shorter leaf end can satisfy a later child when the
    longest cannot (#73 L3). ``alt``/``opt``/``label`` propagate all ends
    inward (``opt`` also offers skip-``pos``); ``rep`` keeps first-hit
    iteration and top-level ``match()`` takes the longest end, so legacy
    single-end preference is preserved. ``budget[0]`` bounds total
    seq-branch attempts from one start; exhaustion yields empty (or, inside
    ``rep``/``opt``/``alt``, the partial alternative), never raises, never
    loops.
    """
    if isinstance(expr, tuple):
        t = cast(tuple[Any, ...], expr)
        if (
            len(t) >= 1
            and isinstance(t[0], str)
            and t[0] in ("seq", "alt", "opt", "rep", "label")
        ):
            kind = cast(str, t[0])
            if kind == "seq":
                children: Any = t[1] if len(t) > 1 else cast(list[Any], [])
                if not isinstance(children, (list, tuple)):
                    return []
                pending: list[int] = [pos]
                for child in cast(Any, children):
                    nxt_pending: list[int] = []
                    for cur in pending:
                        for end in _eval_ends(child, view, cur, leaf_maps, budget):
                            if budget[0] <= 0:
                                return []
                            budget[0] -= 1
                            if end not in nxt_pending:
                                nxt_pending.append(end)
                    pending = nxt_pending
                    if not pending:
                        return []
                # Greedy order: longest end first, so first-hit consumers
                # (top-level match, rep steps) keep legacy preference.
                return sorted(pending, reverse=True)
            if kind == "alt":
                branches: Any = t[1] if len(t) > 1 else cast(list[Any], [])
                if not isinstance(branches, (list, tuple)):
                    return []
                out: list[int] = []
                for branch in cast(Any, branches):
                    for end in _eval_ends(branch, view, pos, leaf_maps, budget):
                        if end not in out:
                            out.append(end)
                return out
            if kind == "opt":
                child = t[1] if len(t) > 1 else None
                if child is None:
                    return [pos]
                ends = _eval_ends(child, view, pos, leaf_maps, budget)
                if pos not in ends:
                    ends = [*ends, pos]
                return ends
            if kind == "rep":
                # First-hit iteration (legacy semantics unchanged): each step
                # takes the first (longest-preferred) end, mirroring the old
                # single-end evaluation exactly.
                child = t[1] if len(t) > 1 else None
                if child is None:
                    return [pos]
                min_rep = 0
                max_rep: int | None = None
                if len(t) > 2:
                    try:
                        min_rep = int(cast(Any, t[2]))
                    except (ValueError, TypeError):
                        min_rep = 0
                if len(t) > 3:
                    try:
                        max_rep = int(cast(Any, t[3]))
                    except (ValueError, TypeError):
                        max_rep = None
                cur = pos
                count = 0
                while True:
                    if max_rep is not None and count >= max_rep:
                        break
                    step = _eval_ends(child, view, cur, leaf_maps, budget)
                    if not step or step[0] == cur:
                        break
                    cur = step[0]
                    count += 1
                    if count > 10000:
                        break
                if count < min_rep:
                    return []
                return [cur]
            if kind == "label":
                child2: Any = t[2] if len(t) > 2 else (t[1] if len(t) > 1 else None)
                if child2 is None:
                    return [pos]
                return _eval_ends(child2, view, pos, leaf_maps, budget)
    if hasattr(cast(Any, expr), "match"):
        attr2 = getattr(cast(Any, expr), "match", None)
        if callable(attr2):
            mp = leaf_maps.get(id(cast(Any, expr)))
            if mp is None:
                return []
            raw = mp.get(pos, [])
            # Tolerate legacy single-end maps ({start: end}) from older
            # callers: normalize to an end list; anything else is no-match
            # (never raise on a malformed map) (#73 L3).
            if isinstance(raw, int):
                return [raw]
            if isinstance(raw, list):
                return [e for e in raw if isinstance(e, int)]
            return []
    if isinstance(expr, str):
        subj = view.subject
        if subj.startswith(expr, pos):
            return [pos + len(expr)]
        return []
    if isinstance(expr, tuple):
        t2 = cast(tuple[Any, ...], expr)
        if len(t2) == 2 and t2[0] == "lit" and isinstance(t2[1], str):
            lit = cast(str, t2[1])
            if view.subject.startswith(lit, pos):
                return [pos + len(lit)]
            return []
        if len(t2) == 2 and t2[0] == "regex" and isinstance(t2[1], str):
            pat_str = cast(str, t2[1])
            try:
                pat = re.compile(pat_str)
            except re.error:
                return []
            m = pat.match(view.subject, pos)
            if m is not None:
                return [m.end()]
            return []
    return []


def _eval_expr(
    expr: Any,
    view: View,
    pos: int,
    leaf_maps: dict[int, dict[int, list[int]]],
) -> int | None:
    """First-hit wrapper over :func:`_eval_ends` (legacy single-end semantics).

    Kept for existing callers: returns the first (longest-preferred) end,
    or ``None`` when the expression yields no end at ``pos``.
    """
    ends = _eval_ends(expr, view, pos, leaf_maps, [_SEQ_EVAL_BUDGET])
    return ends[0] if ends else None


@dataclass(frozen=True, slots=True)
class CombinatorMatcher:
    expr: Any  # expr tree: ("seq", [...]) etc.
    view_name: str | None = None
    view: str | None = None
    anchors: AnchorSet = field(default_factory=AnchorSet)
    boundary: BoundarySpec | None = None
    emit: Callable[[tuple[int, int], Any], Any] | None = None
    predicate: Callable[[str, str], bool] | None = None
    requires_features: frozenset[str] = field(default_factory=lambda: frozenset[str]())
    suppressible: bool = False
    kind: str = field(default="combinator", init=False)
    digest: str = field(init=False, repr=False, default="")

    def __post_init__(self) -> None:
        _validate_emit(self.emit, type(self).__name__)
        if self.view is not None and self.view_name is None:
            object.__setattr__(self, "view_name", self.view)
        elif self.view_name is not None and self.view is None:
            object.__setattr__(self, "view", self.view_name)
        try:
            expr_repr = repr(self.expr)
        except (ValueError, TypeError, AttributeError, RecursionError, RuntimeError):
            expr_repr = str(self.expr)
        view_repr = (
            self.view_name
            if self.view_name is not None
            else (self.view if self.view is not None else "None")
        )
        boundary_repr = repr(self.boundary) if self.boundary is not None else "None"
        anchors_repr = repr(self.anchors)
        pred_repr = (
            getattr(self.predicate, "__qualname__", str(self.predicate))
            if self.predicate is not None
            else "None"
        )
        digest_val = hashlib.sha256(
            f"{expr_repr}\x00{view_repr}\x00{boundary_repr}\x00{anchors_repr}\x00{pred_repr}".encode()
        ).hexdigest()
        object.__setattr__(self, "digest", digest_val)

    def match(self, view: View) -> list[tuple[int, int]]:
        leaves: list[Any] = []
        _collect_leaves(self.expr, leaves)
        seen: set[int] = set()
        uniq_leaves: list[Any] = []
        for lf in leaves:
            iid = id(lf)
            if iid not in seen:
                seen.add(iid)
                uniq_leaves.append(lf)
        leaf_maps: dict[int, dict[int, list[int]]] = {}
        for lf in uniq_leaves:
            spans: list[tuple[int, int]] = []
            try:
                res = cast(Any, lf).match(view)
                if isinstance(res, list):
                    spans = cast(list[tuple[int, int]], res)
            # Matcher-internal boundary (#66): a buggy candidate/leaf/predicate
            # degrades to no-match; grammar-level failures are wrapped as
            # RecognitionError by the orchestrator.
            except (
                re.error,
                ValueError,
                TypeError,
                AttributeError,
                RuntimeError,
                LookupError,
            ):
                spans = []
            mp: dict[int, list[int]] = {}
            for s, e in spans:
                if not isinstance(s, int) or not isinstance(e, int):
                    continue
                ends = mp.setdefault(s, [])
                if e not in ends:
                    ends.append(e)
            for ends in mp.values():
                ends.sort(reverse=True)  # longest-first: legacy preference order
            leaf_maps[id(lf)] = mp

        subj = view.subject
        n = len(subj)
        if n == 0:
            return []
        out: list[tuple[int, int]] = []
        pos = 0
        while pos < n:
            end = _eval_expr(self.expr, view, pos, leaf_maps)
            if end is not None:
                if self.boundary is not None and not check_boundary(
                    subj, pos, end, self.boundary
                ):
                    pos += 1
                    continue
                if self.predicate is not None:
                    try:
                        ok = self.predicate(subj[pos:end], subj)
                    # Matcher-internal boundary (#66): a buggy predicate
                    # degrades to no-match; grammar-level failures are wrapped
                    # as RecognitionError by the orchestrator.
                    except (
                        re.error,
                        ValueError,
                        TypeError,
                        AttributeError,
                        RuntimeError,
                        LookupError,
                    ):
                        ok = False
                    if not ok:
                        pos += 1
                        continue
                if end == pos:
                    pos += 1
                    continue
                out.append((pos, end))
                pos = end
            else:
                pos += 1
        return out
