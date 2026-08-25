"""Lexicon matcher — size-gated alternation / word-anchored dict trie."""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from paxman.core.grammar.anchors import AnchorSet
from paxman.core.grammar.boundary_spec import BoundarySpec, check_boundary
from paxman.core.grammar.lexicon import LexiconAlternation
from paxman.core.grammar.scan_context import View

_check_boundary = check_boundary  # legacy alias for tests

_WORD_RE = re.compile(r"\w", re.UNICODE)


def _build_trie(tokens: frozenset[str]) -> dict[str, Any]:
    trie: dict[str, Any] = {}
    for token in tokens:
        node: dict[str, Any] = trie
        for ch in token:
            nxt_any: Any = node.get(ch)
            if nxt_any is None:
                nxt_any = {}
                node[ch] = nxt_any
            node = nxt_any  # type: ignore[assignment]
        node["_end"] = token
    return trie


@dataclass(frozen=True, slots=True)
class LexiconMatcher:
    """Size-gated lexicon matcher: trie (>500) or alternation (≤500)."""

    tokens: frozenset[str]
    boundary: BoundarySpec | None = None
    view: str | None = None
    anchors: AnchorSet = field(default_factory=AnchorSet)
    emit: Callable[[tuple[int, int], Any], Any] = field(
        default=lambda span, _ctx: span  # type: ignore[no-untyped-def]
    )
    representation: str = "auto"
    requires_features: frozenset[str] = field(default_factory=lambda: frozenset[str]())
    kind: str = field(default="lexicon", init=False)

    _trie: dict[str, Any] | None = field(init=False, repr=False, default=None)
    _compiled: re.Pattern[str] | None = field(init=False, repr=False, default=None)
    _chosen: str = field(init=False, repr=False, default="alternation")

    def __post_init__(self) -> None:
        rep = self.representation
        if rep == "auto":
            rep = "trie" if len(self.tokens) > 500 else "alternation"
        object.__setattr__(self, "_chosen", rep)
        if rep == "alternation":
            alt = LexiconAlternation(tokens=self.tokens, longest_first=True).alternation
            compiled = re.compile(rf"(?:{alt})")
            object.__setattr__(self, "_compiled", compiled)
        else:
            trie = _build_trie(self.tokens)
            object.__setattr__(self, "_trie", trie)

    def match(self, view: View) -> list[tuple[int, int]]:
        if self._chosen == "alternation":
            assert self._compiled is not None
            out: list[tuple[int, int]] = []
            for m in self._compiled.finditer(view.subject):
                s, e = m.start(), m.end()
                if self.boundary is not None and not check_boundary(
                    view.subject, s, e, self.boundary
                ):
                    continue
                out.append((s, e))
            return out
        else:
            assert self._trie is not None
            out_trie: list[tuple[int, int]] = []
            subj = view.subject
            n = len(subj)
            pos = 0
            while pos < n:
                # Word-anchored entry (FlashText model):
                # trie is entered only at word starts.
                if pos > 0 and _WORD_RE.match(subj[pos - 1]) is not None:
                    pos += 1
                    continue
                node2: dict[str, Any] = self._trie
                longest: int | None = None
                j = pos
                while j < n:
                    ch = subj[j]
                    nxt2: Any = node2.get(ch)
                    if nxt2 is None:
                        break
                    node2 = nxt2  # type: ignore[assignment]
                    j += 1
                    if "_end" in node2:
                        e = j
                        ok = True
                        if self.boundary is not None:
                            ok = check_boundary(subj, pos, e, self.boundary)
                        if ok:
                            longest = e
                if longest is not None:
                    out_trie.append((pos, longest))
                    pos = longest
                else:
                    pos += 1
            return out_trie
