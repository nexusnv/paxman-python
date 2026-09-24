"""AmountComposer — S4 fused either-order lexicon+amount span-merge stage.

Implements the hardest Money recognition strategy (ADR-0008 S4): a single
fused regex that matches a currency lexicon token (symbol, word, or
alpha-3 code) adjacent to an amount in *either* order, emitting one
span-bearing ``RecognitionMatch`` per token. This replaces the three
bespoke ``recognize()`` bodies that each hand-rolled the same
``(?:(lex ?amount)|(amount ?lex))`` alternation.

The composer is capability-agnostic: the caller supplies the amount
pattern, the lexicon tokens (or ``None`` for the code case, which uses a
fixed ``[A-Z]{3}`` alternation), the notation builder, the amount-shape
classifier, and the boundary guard. The fused regex is compiled once in
``__post_init__``.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Generic, TypeVar

from paxman.core.domain import RecognitionMatch
from paxman.core.grammar.boundary import BoundaryGuard
from paxman.core.grammar.lexicon import LexiconAlternation
from paxman.core.grammar.stages import PipelineState

NotationT = TypeVar("NotationT")


@dataclass(frozen=True, slots=True)
class AmountComposer(Generic[NotationT]):
    """Fused either-order lexicon+amount recognition stage.

    Builds one regex of the shape
    ``{lookbehind}(?:(?P<prefix_lex>{ALT}) ?(?P<prefix_amt>{pattern})|
    (?P<suffix_amt>{pattern}) ?(?P<suffix_lex>{ALT})){lookahead}`` and, for
    each match, emits a ``RecognitionMatch`` via ``notation_fn``.

    Attributes:
        pattern: The amount sub-pattern (e.g. ``AMOUNT_PATTERN``), supplied
            by the caller. Interpolated **twice** (prefix and suffix
            branches), so it **must not contain named capturing groups** or
            rely on numbered-group indices — violations can fail during regex
            compilation (duplicate group names) or silently shift indices.
            Keep it group-free or use non-capturing ``(?:...)`` only.
        boundary: Boundary guard supplying the lookbehind/lookahead pair.
            Required — a missing guard would silently emit zero matches.
        lexicon_tokens: The currency lexicon (SYMBOL_TOKENS, WORD_TOKENS) or
            ``None`` for the code case, where the alternation is the fixed
            ``[A-Z]{3}``.
        notation_fn: ``(lex, amount, amount_shape) -> Notation`` builder.
        classify: Amount-shape classifier (e.g. ``classify_amount_shape``).
        flags: ``re`` flags passed to ``re.compile`` (e.g. ``re.IGNORECASE``
            for the word case).
    """

    pattern: str
    boundary: BoundaryGuard
    lexicon_tokens: list[str] | set[str] | frozenset[str] | tuple[str, ...] | None = (
        None
    )
    notation_fn: Callable[[str, str, str], NotationT] | None = None
    classify: Callable[[str], str] | None = None
    flags: int = 0

    _compiled: re.Pattern[str] = field(init=False, repr=False)

    def __post_init__(self) -> None:
        """Compile the fused either-order lexicon-plus-amount regex."""
        if self.lexicon_tokens is None:
            alt = r"[A-Z]{3}"
        else:
            alt = LexiconAlternation(
                tokens=self.lexicon_tokens, longest_first=True
            ).alternation
        lookbehind = self.boundary.lookbehind
        lookahead = self.boundary.lookahead
        fused = (
            rf"{lookbehind}"
            rf"(?:(?P<prefix_lex>{alt}) ?(?P<prefix_amt>{self.pattern})"
            rf"|(?P<suffix_amt>{self.pattern}) ?(?P<suffix_lex>{alt}))"
            rf"{lookahead}"
        )
        object.__setattr__(self, "_compiled", re.compile(fused, self.flags))

    def run(self, state: PipelineState[NotationT]) -> PipelineState[NotationT]:
        """Scan text with the fused regex, appending one match per hit."""
        if self.notation_fn is None or self.classify is None:
            return state
        new_matches: list[RecognitionMatch[NotationT]] = list(state.matches)
        for m in self._compiled.finditer(state.text):
            groups = m.groupdict()
            lex = groups["prefix_lex"] or groups["suffix_lex"]
            amt = groups["prefix_amt"] or groups["suffix_amt"]
            if lex is None or amt is None:
                continue
            notation = self.notation_fn(lex, amt, self.classify(amt))
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
