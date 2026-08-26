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
    source_starts: tuple[int, ...] | None
    source_ends: tuple[int, ...] | None
    _text_len: int = field(repr=False)

    @property
    def offsets(self) -> tuple[int, ...] | None:
        if self.source_starts is None or self.source_ends is None:
            return None
        if len(self.source_starts) == 0:
            return (0,)
        return (*self.source_starts, self.source_ends[-1])

    def original_span(self, s: int, e: int) -> tuple[int, int]:
        if self.source_starts is None or self.source_ends is None:
            return (s, e)
        if s == e:
            if len(self.source_starts) == 0:
                return (0, 0)
            if s < len(self.source_starts):
                return (self.source_starts[s], self.source_starts[s])
            return (self.source_ends[-1], self.source_ends[-1])
        return (self.source_starts[s], self.source_ends[e - 1])


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
        self,
        name: str,
        normalizer: Callable[
            [str],
            tuple[str, tuple[int, ...] | None]
            | tuple[str, tuple[int, ...] | None, tuple[int, ...] | None],
        ],
    ) -> View:
        if name in self._views:
            return self._views[name]
        raw: object = normalizer(self.text)
        assert isinstance(raw, tuple)
        if len(raw) == 2:
            subject_obj, offsets_obj = raw  # type: ignore[misc]
            assert isinstance(subject_obj, str)
            subject: str = subject_obj
            if offsets_obj is None:
                starts: tuple[int, ...] | None = None
                ends: tuple[int, ...] | None = None
            else:
                assert isinstance(offsets_obj, tuple)
                starts = tuple(offsets_obj[:-1])  # type: ignore[arg-type]
                if len(starts) == 0:
                    starts = ()
                    ends = ()
                else:
                    ends = tuple(s + 1 for s in starts)
                    assert len(starts) == len(subject)
                    assert len(ends) == len(subject)
        else:
            assert len(raw) == 3
            subject, starts, ends = raw  # type: ignore[misc]
            assert isinstance(subject, str)
            if starts is not None and ends is not None:
                assert isinstance(starts, tuple)
                assert isinstance(ends, tuple)
                assert len(starts) == len(subject), (
                    f"starts len {len(starts)} != subject len {len(subject)}"
                )
                assert len(ends) == len(subject), (
                    f"ends len {len(ends)} != subject len {len(subject)}"
                )
                for i in range(len(subject)):
                    assert 0 <= starts[i] < ends[i] <= len(self.text), (  # type: ignore[index]
                        f"offset interval empty or OOB at {i}: "
                        f"{starts[i]}->{ends[i]} len(text)={len(self.text)}"  # type: ignore[index]
                    )
                    if i > 0:
                        assert starts[i] >= starts[i - 1], (  # type: ignore[index]
                            f"starts non-decreasing violated at {i}: "
                            f"{starts[i - 1]}->{starts[i]}"  # type: ignore[index]
                        )
            elif starts is None and ends is None:
                pass
            else:
                raise AssertionError(
                    "starts and ends must both be None or both be tuple"
                )
        view = View(
            subject=subject,
            source_starts=starts,
            source_ends=ends,
            _text_len=len(self.text),
        )
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
