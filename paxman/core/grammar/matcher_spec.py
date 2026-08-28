"""MatcherSpec — recognition as data."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Literal

from paxman.core.grammar.anchors import AnchorSet
from paxman.core.grammar.boundary_spec import BoundarySpec

MatcherKind = Literal[
    "regex", "lexicon", "scanner", "combinator", "candidates", "label"
]
EmitFn = Callable[[tuple[int, int], Any], Any]


@dataclass(frozen=True, slots=True)
class MatcherSpec:
    """Recognition as data — a declarative matcher in the kernel engine.

    Each spec declares *how* to find a token (``kind`` + ``payload``),
    *where* to search (``view``), *what guards* delimit it (``boundary`` +
    ``anchors``), and *how* to emit a span-bearing notation (``emit``).
    The kernel engine loop (``engine_loop._run_matchers``) compiles these
    into pure functions of ``(spec, snapshot)`` whose digest contributes to
    the recognition revision hash (ADR-0009 §13).

    Attributes:
        kind: Matcher family — one of ``"regex"``, ``"lexicon"``, ``"scanner"``,
            ``"combinator"``, ``"candidates"``, ``"label"``.
        payload: Kind-specific data (pattern string, token set, scanner spec,
            candidate lexeme list, etc.).
        view: Normalized view name to scan (``None`` = original text).
        boundary: Optional declarative boundary guard checked at hit positions.
        anchors: Pre/post-hit anchor requirements that must be satisfied.
        emit: Callable ``((start, end), payload) -> notation`` that produces
            the notation for a hit span.
        requires_features: Feature flags that must be enabled on the contract
            for this matcher to run (``INVALID`` if gated out).
        suppressible: Whether this matcher is eligible for common-word suppression
            when ``suppress_common_words`` is set on the contract.
    """

    kind: MatcherKind
    payload: Any
    view: str | None
    boundary: BoundarySpec | None
    anchors: AnchorSet
    emit: EmitFn
    requires_features: frozenset[str] = frozenset()
    suppressible: bool = False
