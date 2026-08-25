"""ScanContext substrate — one word-span pass, lazy views with offset discipline."""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from paxman.core.grammar.boundary_spec import BoundarySpec

_WordSpans = tuple[tuple[int, int], ...]


@dataclass(frozen=True, slots=True)
class View:
    subject: str
    offsets: tuple[int, ...] | None
    _text_len: int = field(repr=False)

    def original_span(self, s: int, e: int) -> tuple[int, int]:
        if self.offsets is None:
            return (s, e)
        return (self.offsets[s], self.offsets[e])


def _views_factory() -> dict[str, View]:
    return {}


@dataclass(frozen=True, slots=True)
class ScanContext:
    text: str
    word_spans: _WordSpans
    _views: dict[str, View] = field(
        default_factory=_views_factory, repr=False, hash=False, compare=False
    )

    @classmethod
    def of(cls, text: str) -> ScanContext:
        spans: _WordSpans = tuple(
            (m.start(), m.end()) for m in re.finditer(r"\w+", text)
        )
        return cls(text=text, word_spans=spans, _views={})

    def view(
        self, name: str, normalizer: Callable[[str], tuple[str, tuple[int, ...] | None]]
    ) -> View:
        if name in self._views:
            return self._views[name]
        subject, offsets = normalizer(self.text)
        if offsets is not None:
            assert len(offsets) == len(subject) + 1, (
                f"offset map invariant violated: len(offsets)={len(offsets)} "
                f"!= len(subject)+1={len(subject) + 1}"
            )
            for i in range(len(subject)):
                assert 0 <= offsets[i] < offsets[i + 1] <= len(self.text), (
                    f"offset interval empty or OOB at {i}: "
                    f"{offsets[i]}->{offsets[i + 1]} len(text)={len(self.text)}"
                )
        view = View(subject=subject, offsets=offsets, _text_len=len(self.text))
        self._views[name] = view
        return view

    def check_hit(self, text: str, start: int, end: int, spec: BoundarySpec) -> bool:
        """Return True if the hit at ``[start:end)`` respects ``spec`` boundaries.

        Each ``left`` entry is interpreted as a regex that must NOT match the
        suffix ending at ``start``; each ``right`` entry must NOT match the
        prefix starting at ``end``. Mirrors ``(?<!...)`` / ``(?!...)`` guards.
        Delegates to the single-source :func:`check_boundary`.
        """
        from paxman.core.grammar.boundary_spec import check_boundary

        return check_boundary(text, start, end, spec)
