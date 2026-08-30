"""Stage Protocol and concrete stage types for the recognition pipeline."""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Generic, Protocol, TypeVar

from paxman.core.domain import RecognitionMatch
from paxman.core.grammar.boundary import BoundaryGuard
from paxman.core.grammar.lexicon import LexiconAlternation

NotationT = TypeVar("NotationT")


@dataclass(frozen=True, slots=True)
class PipelineState(Generic[NotationT]):
    """Mutable-through-replacement state threaded through stages.

    ``text`` is the original ``recognize()`` input and **must remain unchanged**
    through all stages — stages must place normalized or transformed views in
    ``scratch`` instead, preserving ``RecognitionMatch`` offsets relative to the
    original input. ``matches`` accumulates span-bearing recognitions;
    ``scratch`` is stage-local auxiliary storage.
    """

    text: str
    matches: list[RecognitionMatch[NotationT]] = field(
        default_factory=lambda: list[RecognitionMatch[NotationT]]()
    )
    scratch: dict[str, object] = field(default_factory=lambda: dict[str, object]())


class Stage(Protocol[NotationT]):
    """Inter-stage contract — each stage consumes and returns a PipelineState.

    Every stage **must return a PipelineState with ``state.text`` unchanged**
    from its input. Normalized or transformed text views belong in
    ``state.scratch``, not by mutating ``text``, so ``RecognitionMatch`` spans
    remain relative to the original ``recognize()`` input. Stages may append
    to ``state.matches`` and update ``scratch``.
    """

    def run(self, state: PipelineState[NotationT]) -> PipelineState[NotationT]: ...


@dataclass(frozen=True, slots=True)
class StandardPre(Generic[NotationT]):
    """Pre-processing stage: empty/whitespace early-exit, optional normalizer."""

    empty_guard: bool = True

    def run(self, state: PipelineState[NotationT]) -> PipelineState[NotationT]:
        if self.empty_guard and not state.text.strip():
            return PipelineState(
                text=state.text, matches=[], scratch=dict(state.scratch)
            )
        return state


@dataclass(frozen=True, slots=True)
class RegexStage(Generic[NotationT]):
    """Regex parser stage: pure shape scan via finditer."""

    pattern: str
    notation_fn: Callable[[re.Match[str]], NotationT] | None = None
    flags: int = 0
    _compiled: re.Pattern[str] = field(init=False, repr=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "_compiled", re.compile(self.pattern, self.flags))

    def run(self, state: PipelineState[NotationT]) -> PipelineState[NotationT]:
        if self.notation_fn is None:
            return state
        new_matches: list[RecognitionMatch[NotationT]] = list(state.matches)
        for m in self._compiled.finditer(state.text):
            notation = self.notation_fn(m)
            new_matches.append(
                RecognitionMatch(
                    notation=notation,
                    start=m.start(),
                    end=m.end(),
                    raw_text=m.group(0),
                )
            )
        return PipelineState(
            text=state.text, matches=new_matches, scratch=dict(state.scratch)
        )


@dataclass(frozen=True, slots=True)
class LexiconStage(Generic[NotationT]):
    """Lexicon parser stage: alternation scan guarded by a BoundaryGuard."""

    tokens: frozenset[str] | set[str] | list[str] | tuple[str, ...]
    boundary: BoundaryGuard
    longest_first: bool = True
    notation_fn: Callable[[str], NotationT] | None = None
    flags: int = 0

    _compiled: re.Pattern[str] = field(init=False, repr=False)

    def __post_init__(self) -> None:
        alt = LexiconAlternation(
            tokens=self.tokens, longest_first=self.longest_first
        ).alternation
        object.__setattr__(self, "_compiled", self.boundary.wrap(alt, self.flags))

    def run(self, state: PipelineState[NotationT]) -> PipelineState[NotationT]:
        if self.notation_fn is None:
            return state
        new_matches: list[RecognitionMatch[NotationT]] = list(state.matches)
        for m in self._compiled.finditer(state.text):
            token = m.group(0)
            new_matches.append(
                RecognitionMatch(
                    notation=self.notation_fn(token),
                    start=m.start(),
                    end=m.end(),
                    raw_text=token,
                )
            )
        return PipelineState(
            text=state.text, matches=new_matches, scratch=dict(state.scratch)
        )


@dataclass(frozen=True, slots=True)
class PostStage(Generic[NotationT]):
    """Post-processing stage: applies a transform to each emitted match.

    Used for span-trimming behaviors that the regex span alone cannot
    express — e.g. the E.164 15-digit window trim (end = start +
    len(trimmed_raw)) and the URL paren-balance trim with bare-scheme drop
    (ADR §9.3). The transform maps a ``RecognitionMatch`` to a (possibly
    different) ``RecognitionMatch``, or to ``None`` to drop the match
    entirely. Capability-specific trim logic lives in the grammar file's
    transform closure; this stage stays capability-agnostic.
    """

    transform: Callable[
        [RecognitionMatch[NotationT]], RecognitionMatch[NotationT] | None
    ]

    def run(self, state: PipelineState[NotationT]) -> PipelineState[NotationT]:
        new_matches: list[RecognitionMatch[NotationT]] = []
        for m in state.matches:
            result = self.transform(m)
            if result is not None:
                new_matches.append(result)
        return PipelineState(
            text=state.text, matches=new_matches, scratch=dict(state.scratch)
        )


@dataclass(frozen=True, slots=True)
class WholeInputLookup(Generic[NotationT]):
    """S2 whole-input membership — a LexiconStage variant for Country/name_recognition.

    The entire (trimmed) input is looked up against a set of normalized keys.
    The emitted match carries the *original* trimmed text and span (ADR §5), not the
    normalized key. ``normalizer`` is required: Country must pass its
    ``normalize_name`` so that the lookup key is derived deterministically rather
    than by a hard-coded ``lower()`` that would break other capabilities.
    """

    keys: frozenset[str] | set[str]
    normalizer: Callable[[str], str]
    notation_fn: Callable[[str], NotationT] | None = None

    def run(self, state: PipelineState[NotationT]) -> PipelineState[NotationT]:
        if self.notation_fn is None:
            return state
        trimmed = state.text.strip()
        if not trimmed:
            return state
        normalized = self.normalizer(trimmed)
        if normalized in self.keys:
            start = len(state.text) - len(state.text.lstrip())
            end = start + len(trimmed)
            new_matches: list[RecognitionMatch[NotationT]] = list(state.matches)
            new_matches.append(
                RecognitionMatch(
                    notation=self.notation_fn(trimmed),
                    start=start,
                    end=end,
                    raw_text=trimmed,
                )
            )
            return PipelineState(
                text=state.text, matches=new_matches, scratch=dict(state.scratch)
            )
        return state


@dataclass(frozen=True, slots=True)
class UnicodePropertyStage(Generic[NotationT]):
    """Build-time range stage for \\p{...} (thin alias over RegexStage)."""

    property_name: str
    ranges: tuple[tuple[int, int], ...]
    notation_fn: Callable[[str], NotationT] | None = None
    _compiled: re.Pattern[str] = field(init=False, repr=False)

    def __post_init__(self) -> None:
        parts: list[str] = []
        for start, end in self.ranges:
            if start == end:
                parts.append(re.escape(chr(start)))
            else:
                parts.append(f"{re.escape(chr(start))}-{re.escape(chr(end))}")
        pattern = f"[{''.join(parts)}]"
        object.__setattr__(self, "_compiled", re.compile(pattern))

    def matches(self, ch: str) -> bool:
        """Return True if single char `ch` is in the property (test convenience)."""
        return bool(self._compiled.match(ch))

    def run(self, state: PipelineState[NotationT]) -> PipelineState[NotationT]:
        if self.notation_fn is None:
            return state
        new_matches: list[RecognitionMatch[NotationT]] = list(state.matches)
        for m in self._compiled.finditer(state.text):
            token = m.group(0)
            new_matches.append(
                RecognitionMatch(
                    notation=self.notation_fn(token),
                    start=m.start(),
                    end=m.end(),
                    raw_text=token,
                )
            )
        return PipelineState(
            text=state.text, matches=new_matches, scratch=dict(state.scratch)
        )
