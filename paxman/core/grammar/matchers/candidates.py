"""Candidates matcher — enumerated formats / registry.

Deferred per ADR-0009 §9.6/§15: thin wrapper over ``combinator`` ordered alt
with per-candidate semantics routing (``strategy first|all``). No shipped
grammar uses it on the kernel path yet (Date 4→1, IBAN registry, ISBN
candidates are Phase 3 per ADR §9.6). Fails fast instead of silent ``[]``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

from paxman.core.grammar.anchors import AnchorSet
from paxman.core.grammar.boundary_spec import BoundarySpec
from paxman.core.grammar.scan_context import View


@dataclass(frozen=True, slots=True)
class CandidatesMatcher:
    candidates: tuple[Any, ...] = ()
    strategy: Literal["first", "all"] = "all"
    view_name: str | None = None
    anchors: AnchorSet = field(default_factory=AnchorSet)
    boundary: BoundarySpec | None = None
    requires_features: frozenset[str] = field(default_factory=lambda: frozenset[str]())

    def match(self, view: View) -> list[tuple[int, int]]:
        raise NotImplementedError(
            "CandidatesMatcher not yet implemented — no shipped grammar uses it "
            "on the kernel path (see ADR-0009 §9.6). Date/IBAN/ISBN "
            "candidates remain on PipelineGrammar until this kind lands and its "
            "parity shard is green."
        )
