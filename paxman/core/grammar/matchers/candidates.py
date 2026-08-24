"""Candidates matcher — enumerated formats / registry."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

from paxman.core.grammar.anchors import AnchorSet
from paxman.core.grammar.scan_context import View


@dataclass(frozen=True, slots=True)
class CandidatesMatcher:
    candidates: tuple[Any, ...] = ()
    strategy: Literal["first", "all"] = "all"
    view_name: str | None = None
    anchors: AnchorSet = field(default_factory=AnchorSet)

    def match(self, view: View) -> list[tuple[int, int]]:
        return []
