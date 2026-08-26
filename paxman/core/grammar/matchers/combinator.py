"""Combinator matcher — seq/alt/opt/rep/label over child specs.

Deferred per ADR-0009 §9.4/§15: the combinator kind is a thin ergonomic wrapper
over child specs evaluated left-to-right with span capture (nom/winnow IResult
model). The kind is declared here so ``MatcherKind`` is complete and
``MatcherSpec`` validation can reference it, but no shipped grammar yet uses it
on the kernel engine path — Money/SIUnit compound/BCP47 migrations that need it
remain on ``PipelineGrammar`` until their parity shards are green. A call to
:meth:`match` therefore fails fast instead of silently returning ``MISSING``.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from paxman.core.grammar.anchors import AnchorSet
from paxman.core.grammar.boundary_spec import BoundarySpec
from paxman.core.grammar.matchers._emit_validation import (
    validate_emit as _validate_emit,
)
from paxman.core.grammar.scan_context import View


@dataclass(frozen=True, slots=True)
class CombinatorMatcher:
    expr: Any  # expr tree: ("seq", [...]) etc.
    view_name: str | None = None
    anchors: AnchorSet = field(default_factory=AnchorSet)
    boundary: BoundarySpec | None = None
    emit: Callable[[tuple[int, int], Any], Any] | None = None
    predicate: Callable[[str, str], bool] | None = None
    requires_features: frozenset[str] = field(default_factory=lambda: frozenset[str]())

    def __post_init__(self) -> None:
        _validate_emit(self.emit, type(self).__name__)

    def match(self, view: View) -> list[tuple[int, int]]:
        raise NotImplementedError(
            "CombinatorMatcher not yet implemented — no shipped grammar uses it on the "
            "kernel path (see ADR-0009 §9.4). Wire the grammar to "
            "PipelineGrammar until the combinator engine lands and its parity shard "
            "tests/property/test_combinator_parity.py is green."
        )
