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
                children = t[1] if len(t) > 1 else []
                if isinstance(children, (list, tuple)):
                    cl = cast(list[Any], list(children))
                    for ch in cl:
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
    if hasattr(expr, "match"):
        attr = getattr(expr, "match", None)
        if callable(attr):
            out.append(expr)


def _eval_expr(
    expr: Any,
    view: View,
    pos: int,
    leaf_maps: dict[int, dict[int, int]],
) -> int | None:
    if isinstance(expr, tuple):
        t = cast(tuple[Any, ...], expr)
        if (
            len(t) >= 1
            and isinstance(t[0], str)
            and t[0] in ("seq", "alt", "opt", "rep", "label")
        ):
            kind = cast(str, t[0])
            if kind == "seq":
                children: Any = t[1] if len(t) > 1 else []
                cur = pos
                if not isinstance(children, (list, tuple)):
                    return None
                cl = cast(list[Any], list(children))
                for child in cl:
                    nxt = _eval_expr(child, view, cur, leaf_maps)
                    if nxt is None:
                        return None
                    cur = nxt
                return cur
            if kind == "alt":
                branches: Any = t[1] if len(t) > 1 else []
                if not isinstance(branches, (list, tuple)):
                    return None
                bl = cast(list[Any], list(branches))
                for branch in bl:
                    nxt = _eval_expr(branch, view, pos, leaf_maps)
                    if nxt is not None:
                        return nxt
                return None
            if kind == "opt":
                child = t[1] if len(t) > 1 else None
                if child is None:
                    return pos
                nxt = _eval_expr(child, view, pos, leaf_maps)
                if nxt is None:
                    return pos
                return nxt
            if kind == "rep":
                child = t[1] if len(t) > 1 else None
                if child is None:
                    return pos
                min_rep = 0
                max_rep: int | None = None
                if len(t) > 2:
                    try:
                        min_rep = int(cast(Any, t[2]))
                    except Exception:
                        min_rep = 0
                if len(t) > 3:
                    try:
                        max_rep = int(cast(Any, t[3]))
                    except Exception:
                        max_rep = None
                cur = pos
                count = 0
                while True:
                    if max_rep is not None and count >= max_rep:
                        break
                    nxt = _eval_expr(child, view, cur, leaf_maps)
                    if nxt is None or nxt == cur:
                        break
                    cur = nxt
                    count += 1
                    if count > 10000:
                        break
                if count < min_rep:
                    return None
                return cur
            if kind == "label":
                child2: Any = t[2] if len(t) > 2 else (t[1] if len(t) > 1 else None)
                if child2 is None:
                    return pos
                return _eval_expr(child2, view, pos, leaf_maps)
    if hasattr(expr, "match"):
        attr2 = getattr(expr, "match", None)
        if callable(attr2):
            mp = leaf_maps.get(id(expr))
            if mp is None:
                return None
            return mp.get(pos)
    if isinstance(expr, str):
        subj = view.subject
        if subj.startswith(expr, pos):
            return pos + len(expr)
        return None
    if isinstance(expr, tuple):
        t2 = cast(tuple[Any, ...], expr)
        if len(t2) == 2 and t2[0] == "lit" and isinstance(t2[1], str):
            lit = cast(str, t2[1])
            if view.subject.startswith(lit, pos):
                return pos + len(lit)
            return None
        if len(t2) == 2 and t2[0] == "regex" and isinstance(t2[1], str):
            pat_str = cast(str, t2[1])
            try:
                pat = re.compile(pat_str)
            except re.error:
                return None
            m = pat.match(view.subject, pos)
            if m is not None:
                return m.end()
            return None
    return None


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
        except Exception:
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
        leaf_maps: dict[int, dict[int, int]] = {}
        for lf in uniq_leaves:
            spans: list[tuple[int, int]] = []
            try:
                res = cast(Any, lf).match(view)
                if isinstance(res, list):
                    spans = cast(list[tuple[int, int]], res)
            except Exception:
                spans = []
            mp: dict[int, int] = {}
            for s, e in spans:
                if not isinstance(s, int) or not isinstance(e, int):
                    continue
                if s not in mp or e > mp[s]:
                    mp[s] = e
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
                    except Exception:
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
