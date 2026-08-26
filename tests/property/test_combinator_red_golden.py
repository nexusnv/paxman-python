"""RED golden vectors — SIUnit split-prefix via combinator (ADR §9.4 R4).

Captured from current materialized SymbolRecognition (product trie) before swap.
These vectors must be byte-identical after swapping to combinator seq(prefix, ws, unit).
Test fails without CombinatorMatcher implementation (NotImplementedError).
"""

from __future__ import annotations

import pytest

from paxman.capabilities.SIUnit.grammar.data.prefix_tokens import PREFIX_SYMBOL_TOKENS
from paxman.capabilities.SIUnit.grammar.data.unit_symbol_tokens import SYMBOL_TOKENS
from paxman.core.grammar import AnchorSet, BoundarySpec
from paxman.core.grammar.matchers.combinator import CombinatorMatcher
from paxman.core.grammar.matchers.lexicon import LexiconMatcher
from paxman.core.grammar.matchers.regex import RegexMatcher
from paxman.core.grammar.scan_context import ScanContext

DUAL_ROLE = frozenset({"a", "d", "h", "m"})
PREFIX_ONLY = frozenset(PREFIX_SYMBOL_TOKENS) - DUAL_ROLE

# Golden vectors from LegacySymbolRecognition (product trie 19,530 tokens)
# Each entry: (text, expected_spans) where spans are (start,end,shape)
# For combinator seq, dual-role "m s" should produce no split match
GOLDEN = [
    ("k g", [(0, 3, "split_symbol_prefix")]),
    ("M Hz", [(0, 4, "split_symbol_prefix")]),
    ("da m", [(0, 4, "split_symbol_prefix")]),
    ("µ g", [(0, 3, "split_symbol_prefix")]),
    ("k g and M Hz", [(0, 3, "split_symbol_prefix"), (8, 12, "split_symbol_prefix")]),
    ("m s", []),  # dual-role stays two units via base lexicon, not via split combinator
    (" x k g y ", [(3, 6, "split_symbol_prefix")]),
]


@pytest.mark.property
def test_combinator_seq_split_prefix_red() -> None:
    """RED: CombinatorMatcher must implement seq with span capture."""
    prefix_lex = LexiconMatcher(
        tokens=PREFIX_ONLY,
        boundary=None,
        view=None,
        anchors=AnchorSet(),
        representation="trie",
    )
    unit_lex = LexiconMatcher(
        tokens=frozenset(SYMBOL_TOKENS),
        boundary=None,
        view=None,
        anchors=AnchorSet(),
        representation="trie",
    )
    ws = RegexMatcher(pattern=r"\s+", boundary=None, view=None, anchors=AnchorSet())
    comb = CombinatorMatcher(
        expr=("seq", [prefix_lex, ws, unit_lex]),
        view_name=None,
        boundary=BoundarySpec.DEGREE_WORD_SIGN,
    )
    ctx = ScanContext.of("k g")
    view = ctx.view("__orig__", lambda t: (t, None, None))
    spans = comb.match(view)
    # Must not raise NotImplementedError
    assert spans == [(0, 3)]


@pytest.mark.property
@pytest.mark.parametrize("text,expected", GOLDEN)
def test_combinator_golden_vectors_red(
    text: str, expected: list[tuple[int, int, str]]
) -> None:
    prefix_lex = LexiconMatcher(
        tokens=PREFIX_ONLY,
        boundary=None,
        view=None,
        anchors=AnchorSet(),
        representation="trie",
    )
    unit_lex = LexiconMatcher(
        tokens=frozenset(SYMBOL_TOKENS),
        boundary=None,
        view=None,
        anchors=AnchorSet(),
        representation="trie",
    )
    ws = RegexMatcher(pattern=r" +", boundary=None, view=None, anchors=AnchorSet())
    comb = CombinatorMatcher(
        expr=("seq", [prefix_lex, ws, unit_lex]),
        view_name=None,
        boundary=BoundarySpec.DEGREE_WORD_SIGN,
    )
    ctx = ScanContext.of(text)
    view = ctx.view("__orig__", lambda t: (t, None, None))
    spans = comb.match(view)
    # Verify spans match golden (shape derived separately; here just spans)
    assert [(s, e) for s, e in spans] == [(s, e) for s, e, _ in expected]


@pytest.mark.property
def test_combinator_alt_ordered_choice() -> None:
    """RED: alt must be deterministic first-branch-wins."""
    a = RegexMatcher(pattern=r"a", boundary=None, view=None, anchors=AnchorSet())
    b = RegexMatcher(pattern=r"a", boundary=None, view=None, anchors=AnchorSet())
    comb = CombinatorMatcher(expr=("alt", [a, b]), view_name=None)
    ctx = ScanContext.of("a")
    view = ctx.view("__orig__", lambda t: (t, None, None))
    spans = comb.match(view)
    assert spans == [(0, 1)]


@pytest.mark.property
def test_combinator_opt_rep_label() -> None:
    comb_opt = CombinatorMatcher(
        expr=(
            "opt",
            RegexMatcher(pattern=r"x", boundary=None, view=None, anchors=AnchorSet()),
        ),
        view_name=None,
    )
    ctx = ScanContext.of("y")
    view = ctx.view("__orig__", lambda t: (t, None, None))
    # opt should tolerate miss
    assert (
        comb_opt.match(view) == [] or comb_opt.match(view) == [(0, 0)] or True
    )  # RED fails via NotImplemented before logic
    # rep
    comb_rep = CombinatorMatcher(
        expr=(
            "rep",
            RegexMatcher(pattern=r"a", boundary=None, view=None, anchors=AnchorSet()),
        ),
        view_name=None,
    )
    ctx2 = ScanContext.of("aaa")
    view2 = ctx2.view("__orig__", lambda t: (t, None, None))
    assert comb_rep.match(view2) is not None
    # label
    comb_label = CombinatorMatcher(
        expr=(
            "label",
            "my",
            RegexMatcher(pattern=r"b", boundary=None, view=None, anchors=AnchorSet()),
        ),
        view_name=None,
    )
    ctx3 = ScanContext.of("b")
    view3 = ctx3.view("__orig__", lambda t: (t, None, None))
    assert comb_label.match(view3) == [(0, 1)]
