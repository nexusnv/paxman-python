"""Compound recognition grammar for SI Unit (staged pipeline).

Recognizes product/quotient compound shapes over unit symbols: UNIT
(separator UNIT){1,3} where each UNIT is a symbol character run with an
optional exponent, and the separator is "/", "·" or "⋅" (D3). The
grammar is shape-only: it does not validate that the units are known
(the ISO 80000-1 rule does that). "m/s²", "N·m", "kg·m/s²", "g/cm³"
are recognized as single spans; "m s" (space) is not a compound.

The single bespoke regex from the legacy grammar is reproduced exactly
as a ``RegexStage`` body guarded by ``BoundaryGuard.word_sign()`` (the
compound boundary has no degree prefix, matching the legacy
lookarounds). The notation factory emits the compound body verbatim.
"""

from __future__ import annotations

import re

from paxman.capabilities.SIUnit.grammar.data.compound_tokens import (
    COMPOUND_SEPARATORS,
    EXPONENT_CHARACTERS,
)
from paxman.capabilities.SIUnit.notation import SIUnitNotation
from paxman.core.grammar import BoundaryGuard, PipelineGrammar, RegexStage, StandardPre

# Shape constants come from the Task 4 generated module (grammars may import
# from grammar/data/ — only rules are barred by the grammar↔rules purity
# scan). Keeps the separator/exponent characters in one place.
_EXPONENT = rf"[{EXPONENT_CHARACTERS}]*"
_UNIT = rf"(?:°?[A-Za-zµΩÅ][A-Za-zµΩÅ0-9]*{_EXPONENT})"
_SEP = f"[{COMPOUND_SEPARATORS}]"
# A factor is either a bare unit or a parenthesized group of 1–4 units
# joined by separators. ISO 80000-1 §6.6.2 prescribes parentheses as the
# disambiguation for a solidus followed by another separator, so a
# parenthesized denominator is a single compound factor (e.g. "(m·s²)").
_FACTOR = rf"(?:{_UNIT}|\({_UNIT}(?:{_SEP}{_UNIT}){{0,3}}\))"
# The word_sign guard reproduces the legacy compound lookarounds exactly
# (no degree prefix in the compound boundary) — no hard-coded lookaround in
# this file (ADR-0009 §10).
_GUARD = BoundaryGuard.word_sign()
_COMPOUND_PATTERN = (
    _GUARD.lookbehind
    + r"(?P<body>"
    + _FACTOR
    + r"(?:"
    + _SEP
    + _FACTOR
    + r"){1,3})"
    + _GUARD.lookahead
)


def _compound_notation(match: re.Match[str]) -> SIUnitNotation:
    """Emit the compound body verbatim with shape "compound"."""
    return SIUnitNotation(text=match.group("body"), shape="compound")


class CompoundRecognition(PipelineGrammar[SIUnitNotation]):
    """Grammar: compound_recognition — product/quotient unit shapes."""

    name = "compound_recognition"
    semantics = "compound_recognition"  # SEAM (ADR-0003): identity id

    pre = StandardPre[SIUnitNotation](empty_guard=True)
    regex = RegexStage[SIUnitNotation](
        pattern=_COMPOUND_PATTERN,
        notation_fn=_compound_notation,
    )
