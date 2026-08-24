"""AnchorSet T0 prefilter — necessary conditions, C-speed."""

from __future__ import annotations

import re
from dataclasses import dataclass

from paxman.core.grammar.scan_context import ScanContext


@dataclass(frozen=True, slots=True)
class AnchorSet:
    """Necessary-condition prefilter evaluated before scanning."""

    literals: frozenset[str] = frozenset()
    classes: tuple[str, ...] = ()
    key_sets: tuple[frozenset[str], ...] = ()
    _class_res: tuple[re.Pattern[str], ...] = ()

    def passes(self, text: str, ctx: ScanContext) -> bool:
        for lit in self.literals:
            if lit not in text:
                return False
        patterns: tuple[re.Pattern[str], ...]
        if self._class_res:
            patterns = self._class_res
        elif self.classes:
            patterns = tuple(re.compile(p) for p in self.classes)
        else:
            patterns = ()
        for pat in patterns:
            if pat.search(text) is None:
                return False
        for ks in self.key_sets:
            if not any(ctx.text[s] in ks for s, _ in ctx.word_spans):
                return False
        return True


@dataclass(frozen=True, slots=True)
class HasDigit:
    """Class anchor for digit presence."""

    def as_set(self) -> AnchorSet:
        return AnchorSet(
            literals=frozenset(),
            classes=(r"\d",),
            key_sets=(),
            _class_res=(re.compile(r"\d"),),
        )


@dataclass(frozen=True, slots=True)
class LiteralAnchor:
    """Literal anchor for substring presence."""

    literal: str

    def as_set(self) -> AnchorSet:
        return AnchorSet(literals=frozenset({self.literal}))


@dataclass(frozen=True, slots=True)
class KeySetAnchor:
    """Key-set anchor for word-initial character presence."""

    keys: frozenset[str]

    def as_set(self) -> AnchorSet:
        return AnchorSet(literals=frozenset(), classes=(), key_sets=(self.keys,))
