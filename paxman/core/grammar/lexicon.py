"""LexiconAlternation builder — longest-first, qualified-first, escaped."""

from __future__ import annotations

import re
from dataclasses import dataclass, field


def _is_qualified(token: str) -> bool:
    """Return whether a token carries at least one ASCII alphabetic character.

    Mirrors ``Currency/SymbolRecognition._is_qualified``: a token that contains
    an ASCII letter (e.g. ``"US$"``) is "qualified" and sorts ahead of a bare
    symbol (e.g. ``"$"``) of the same length, so the longer/qualified form is
    tried first by the regex engine and wins the match.
    """
    return any(c.isascii() and c.isalpha() for c in token)


@dataclass(frozen=True, slots=True)
class LexiconAlternation:
    """Builds a longest-first, qualified-first escaped alternation.

    Tokens are sorted by ``(-len(token), -is_qualified, token)`` and joined with
    ``|`` after ``re.escape``. This reproduces the ``SYMBOL_TOKENS`` duplication
    between Currency and Money without per-file copy-paste (ADR-0008 D4).
    """

    tokens: frozenset[str] | set[str] | list[str] | tuple[str, ...]
    longest_first: bool = True

    ordered_tokens: list[str] = field(init=False)
    alternation: str = field(init=False)

    def __post_init__(self) -> None:
        """Sort tokens and build the escaped alternation string."""
        toks = list(self.tokens)
        if self.longest_first:
            toks.sort(key=lambda t: (-len(t), -int(_is_qualified(t)), t))
        else:
            toks.sort()
        object.__setattr__(self, "ordered_tokens", toks)
        object.__setattr__(self, "alternation", "|".join(re.escape(t) for t in toks))
