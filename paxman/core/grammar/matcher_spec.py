"""MatcherSpec — recognition as data."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Literal

from paxman.core.grammar.anchors import AnchorSet
from paxman.core.grammar.boundary_spec import BoundarySpec

MatcherKind = Literal[
    "regex", "lexicon", "scanner", "combinator", "property", "candidates", "label"
]
EmitFn = Callable[[tuple[int, int], Any], Any]


@dataclass(frozen=True, slots=True)
class MatcherSpec:
    kind: MatcherKind
    payload: Any
    view: str | None
    boundary: BoundarySpec | None
    anchors: AnchorSet
    emit: EmitFn
    requires_features: frozenset[str] = frozenset()
    suppressible: bool = False
