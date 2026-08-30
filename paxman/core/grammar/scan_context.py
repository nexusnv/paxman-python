"""ScanContext substrate — one word-span pass, lazy two-array views.

(source_starts/source_ends) with offset discipline. Views materialized once
per name; shared substrate for scan() batch."""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, cast

if TYPE_CHECKING:
    from paxman.core.grammar.boundary_spec import BoundarySpec

_WordSpans = tuple[tuple[int, int], ...]


@dataclass(frozen=True, slots=True)
class View:
    """A normalized view over the original text with source offset mapping.

    Each view carries a normalized ``subject`` (the text after a normalizer
    such as case-fold or accent-strip) plus parallel ``source_starts`` /
    ``source_ends`` arrays that map every character in ``subject`` back to
    its half-open ``[start, end)`` interval in the original ``ScanContext.text``.
    ``None`` for both arrays means the normalizer is the identity (no offset
    translation needed).

    Attributes:
        subject: Normalized text for this view.
        source_starts: Start offsets in the original text, one per character
            in ``subject``, or ``None`` for the identity view.
        source_ends: End offsets in the original text, one per character
            in ``subject``, or ``None`` for the identity view.
        stripped_chars: Characters the normalizer strips that legacy matchers
            may re-absorb into their emitted spans (e.g. ``"\\t\\n\\r"`` for
            the IDNA view), or ``None`` when the view has no such set.
    """

    subject: str
    source_starts: tuple[int, ...] | None
    source_ends: tuple[int, ...] | None
    _text_len: int = field(repr=False)
    stripped_chars: str | None = field(default=None, repr=False)

    @property
    def offsets(self) -> tuple[int, ...] | None:
        """Return the combined offset array for this view, or None for identity.

        For non-identity views this returns ``(*source_starts, source_ends[-1])``
        — the boundary offsets that reconstruct original spans. ``None`` signals
        that view spans map 1:1 to original spans. Empty views return ``(0,)``.
        """
        if self.source_starts is None or self.source_ends is None:
            return None
        if len(self.source_starts) == 0:
            return (0,)
        return (*self.source_starts, self.source_ends[-1])

    def original_span(self, s: int, e: int) -> tuple[int, int]:
        """Translate a view span back to the original text span.

        Args:
            s: Start offset in the normalized view subject.
            e: End offset in the normalized view subject (half-open).

        Returns:
            Half-open ``(start, end)`` in the original ``ScanContext.text``.
            Identity views return the input span unchanged; empty view spans
            map to ``(0, 0)``.
        """
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
    """Scan substrate — one word-span pass, shared across a batch scan.

    Canonicalization's recognition substrate: the original ``text``, its
    precomputed ``word_spans`` (half-open ``[start, end)`` for each ``\\w+``
    match), and a lazy cache of normalized ``views``. The substrate is built
    once per ``scan()`` / ``canonicalize()`` call and reused for every
    contract/grammar in the batch, guaranteeing F1×F6 (single-value + invisible
    embedded values) as an API property rather than a caller obligation.

    Views use a two-array tuple ``(subject, starts, ends)`` discipline where
    ``starts[i]`` / ``ends[i]`` is the original interval for ``subject[i]``.
    They are materialized once per name and then cached; subsequent ``view()``
    calls for the same name return the cached instance.

    Attributes:
        text: Original input text being scanned.
        word_spans: Tuple of ``(start, end)`` for each ``\\w+`` word span
            in ``text``, used for common-word suppression.
        _views: Internal cache of materialized views keyed by normalizer name.
    """

    text: str
    word_spans: _WordSpans
    _views: dict[str, View] = field(
        default_factory=_views_factory, repr=False, hash=False, compare=False
    )

    @classmethod
    def of(cls, text: str) -> ScanContext:
        """Create a ScanContext for the given text.

        Performs the single ``\\w+`` word-span pass that underlies
        common-word suppression and view-discipline checks.

        Args:
            text: Raw input text to scan.

        Returns:
            A new ``ScanContext`` with ``word_spans`` precomputed and an
            empty view cache.
        """
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
        stripped_chars: str | None = None,
    ) -> View:
        """Return (or lazily materialize) a named normalized view.

        The normalizer is called at most once per ``name``; the resulting
        ``View`` is cached in ``_views`` and returned on subsequent calls.
        Normalizers may return either a 2-tuple ``(subject, offsets)`` (single
        array, expanded to starts/ends with unit width) or a 3-tuple
        ``(subject, starts, ends)`` (explicit two-array discipline). Both
        ``starts`` and ``ends`` must be ``None`` together or ``tuple`` together,
        and when present must be the same length as ``subject`` with valid,
        non-decreasing intervals.

        Args:
            name: Cache key for this view (e.g. the normalizer's registered name).
            normalizer: Callable that maps the original text to ``(subject, offsets)``
                or ``(subject, starts, ends)``.
            stripped_chars: Characters stripped by the normalizer that matchers
                may re-absorb into spans; recorded on the View.

        Returns:
            The cached or newly materialized ``View`` for ``name``.
        """
        if name in self._views:
            return self._views[name]
        raw: object = normalizer(self.text)
        assert isinstance(raw, tuple)
        if len(raw) == 2:
            raw2 = cast(tuple[str, tuple[int, ...] | None], raw)
            subject_obj, offsets_obj = raw2
            assert isinstance(subject_obj, str)
            subject: str = subject_obj
            if offsets_obj is None:
                starts: tuple[int, ...] | None = None
                ends: tuple[int, ...] | None = None
            else:
                assert isinstance(offsets_obj, tuple)
                offsets_tuple = cast(tuple[int, ...], offsets_obj)
                starts = tuple(offsets_tuple[:-1])
                if len(starts) == 0:
                    starts = ()
                    ends = ()
                else:
                    ends = tuple(s + 1 for s in starts)
                    assert len(starts) == len(subject)
                    assert len(ends) == len(subject)
                    for i in range(len(subject)):
                        assert 0 <= starts[i] < ends[i] <= len(self.text), (
                            f"offset interval empty or OOB at {i}: "
                            f"{starts[i]}->{ends[i]} len(text)={len(self.text)}"
                        )
                        if i > 0:
                            assert starts[i] >= starts[i - 1], (
                                f"starts non-decreasing violated at {i}: "
                                f"{starts[i - 1]}->{starts[i]}"
                            )
                            assert ends[i] >= ends[i - 1], (
                                f"ends non-decreasing violated at {i}: "
                                f"{ends[i - 1]}->{ends[i]}"
                            )
        else:
            assert len(raw) == 3
            raw3 = cast(tuple[str, tuple[int, ...] | None, tuple[int, ...] | None], raw)
            subject, starts, ends = raw3
            assert isinstance(subject, str)
            if starts is not None and ends is not None:
                assert isinstance(starts, tuple)
                assert isinstance(ends, tuple)
                starts_nn = cast(tuple[int, ...], starts)
                ends_nn = cast(tuple[int, ...], ends)
                assert len(starts_nn) == len(subject), (
                    f"starts len {len(starts_nn)} != subject len {len(subject)}"
                )
                assert len(ends_nn) == len(subject), (
                    f"ends len {len(ends_nn)} != subject len {len(subject)}"
                )
                for i in range(len(subject)):
                    assert 0 <= starts_nn[i] < ends_nn[i] <= len(self.text), (
                        f"offset interval empty or OOB at {i}: "
                        f"{starts_nn[i]}->{ends_nn[i]} len(text)={len(self.text)}"
                    )
                    if i > 0:
                        assert starts_nn[i] >= starts_nn[i - 1], (
                            f"starts non-decreasing violated at {i}: "
                            f"{starts_nn[i - 1]}->{starts_nn[i]}"
                        )
                        assert ends_nn[i] >= ends_nn[i - 1], (
                            f"ends non-decreasing violated at {i}: "
                            f"{ends_nn[i - 1]}->{ends_nn[i]}"
                        )
                starts = starts_nn
                ends = ends_nn
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
            stripped_chars=stripped_chars,
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
