"""Element recognition grammar — one grammar, three kernel matchers.

Recognizes human element designations without assigning canonical meaning:

- symbol branch: case-exact ``LexiconMatcher`` over ``SYMBOL_KEYS``
  (118 canonical proper-case symbols plus 118 all-lowercase forms) with an
  isotope/formula guard — ``fe`` folds to ``Fe`` at emit, while ``FE``
  stays unclaimed by design (no all-caps keys);
- name branch: case-insensitive ``LexiconMatcher`` over ``NAME_KEYS``
  (120 lowercase names) on the ``casefolded`` view — the raw span is
  lowercased at emit;
- atomic-number branch: label-required ``RegexMatcher`` — the label
  (``element`` | ``atomic number`` | ``Z``) plus a non-empty separator is
  part of the pattern itself, so bare ``26`` is never claimed. The emit
  re-searches the raw span for the digit core and folds leading zeros
  via ``int()`` (``026`` → ``26``).

Recognition only: no validation, no token-to-symbol mapping (rules own
every such decision). No custom ``recognize()`` override — the
``PipelineGrammar`` base delegates to the engine-owned matcher loop and
the engine deduplicates overlapping spans.
"""

from __future__ import annotations

import re as _re

from paxman.capabilities.Element.grammar.data.element_keys import (
    NAME_KEYS,
    SYMBOL_KEYS,
)
from paxman.capabilities.Element.notation import ElementNotation
from paxman.core.grammar import (
    AnchorSet,
    BoundarySpec,
    PipelineGrammar,
    StandardPre,
)
from paxman.core.grammar.matchers.lexicon import LexiconMatcher
from paxman.core.grammar.matchers.regex import RegexMatcher
from paxman.core.grammar.scan_context import ScanContext


def _emit_symbol(span: tuple[int, int], ctx: ScanContext) -> ElementNotation:
    s, e = span
    raw = ctx.text[s:e]
    return ElementNotation(token=raw[0].upper() + raw[1:].lower(), shape="symbol")


def _emit_name(span: tuple[int, int], ctx: ScanContext) -> ElementNotation:
    s, e = span
    raw = ctx.text[s:e]
    return ElementNotation(token=raw.lower(), shape="name")


def _emit_z(span: tuple[int, int], ctx: ScanContext) -> ElementNotation:
    raw = ctx.text[span[0] : span[1]]
    # [0-9] matches ASCII digits only (unlike \d), so this re-search cannot
    # diverge from the (?a)-flagged pattern core into a Unicode digit run.
    found = _re.search(r"[0-9]{1,3}", raw)
    digits = found.group(0) if found is not None else raw
    return ElementNotation(token=str(int(digits)), shape="atomic_number")


_Z_PATTERN = r"(?ai:(?:element|atomic number|Z)[\s:=]+[0-9]{1,3})(?![0-9])"

_Z_MATCHER = RegexMatcher(
    pattern=_Z_PATTERN,
    boundary=BoundarySpec.WORD,
    view=None,
    anchors=AnchorSet(),
    emit=_emit_z,
    suppressible=False,
)

_SYMBOL_MATCHER = LexiconMatcher(
    tokens=SYMBOL_KEYS,
    boundary=BoundarySpec(left=("\\w",), right=("\\w", "-\\d")),
    view=None,
    anchors=AnchorSet(),
    emit=_emit_symbol,
    representation="auto",
    suppressible=True,
)

_NAME_MATCHER = LexiconMatcher(
    tokens=NAME_KEYS,
    boundary=BoundarySpec.WORD,
    view="casefolded",
    anchors=AnchorSet(),
    emit=_emit_name,
    representation="auto",
    suppressible=False,
)


class ElementRecognitionGrammar(PipelineGrammar[ElementNotation]):
    """Grammar: element_recognition — symbols, names, labeled atomic numbers."""

    name = "element_recognition"
    semantics = "element_recognition"
    single_value = True

    pre = StandardPre[ElementNotation](empty_guard=True)
    matchers = (_Z_MATCHER, _SYMBOL_MATCHER, _NAME_MATCHER)
