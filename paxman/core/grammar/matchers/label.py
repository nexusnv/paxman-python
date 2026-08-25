"""Label matcher — optional label + value fusion.

Deferred per ADR-0009 §9.7/§15: unifies per-file ``[\\s:-]+`` vs ``[\\s:-]*``
conventions as ``glued_policy reject|allow``. No shipped grammar uses it on
the kernel path yet (BIC/IBAN/ORCID/ISSN/ISBN label migrations are Phase 3).
``matches_prefix`` is the tested utility; :meth:`match` fails fast until the
kind is wired to a value matcher and its parity shard is green.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Literal

from paxman.core.grammar.anchors import AnchorSet
from paxman.core.grammar.boundary_spec import BoundarySpec
from paxman.core.grammar.scan_context import View


@dataclass(frozen=True, slots=True)
class LabelMatcher:
    labels: frozenset[str] = frozenset()
    separator: str = r"[\s:-]+"
    glued_policy: Literal["reject", "allow"] = "reject"
    view_name: str | None = None
    anchors: AnchorSet = field(default_factory=AnchorSet)
    boundary: BoundarySpec | None = None
    requires_features: frozenset[str] = field(default_factory=lambda: frozenset[str]())
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
        raise NotImplementedError(
            "LabelMatcher.match not yet implemented — no shipped grammar uses it "
            "on the kernel path (see ADR-0009 §9.7, plan Task 8). Label migrations "
            "remain on PipelineGrammar RegexStage until this kind lands."
        )
