"""Label matcher — optional label + value fusion."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Literal

from paxman.core.grammar.anchors import AnchorSet
from paxman.core.grammar.scan_context import View


@dataclass(frozen=True, slots=True)
class LabelMatcher:
    labels: frozenset[str] = frozenset()
    separator: str = r"[\s:-]+"
    glued_policy: Literal["reject", "allow"] = "reject"
    view_name: str | None = None
    anchors: AnchorSet = field(default_factory=AnchorSet)
    _sep_re: re.Pattern[str] | None = field(init=False, repr=False, default=None)

    def __post_init__(self) -> None:
        object.__setattr__(self, "_sep_re", re.compile(self.separator))

    def matches_prefix(self, text: str) -> bool:
        sep_re = self._sep_re
        assert sep_re is not None
        for label in self.labels:
            if text.startswith(label):
                rest = text[len(label) :]
                if not rest:
                    return False
                if self.glued_policy == "reject":
                    return sep_re.match(rest) is not None
                else:
                    return True
        return False

    def match(self, view: View) -> list[tuple[int, int]]:
        return []
