"""#73 L3 — combinator seq explores every leaf alternative end (backtracking).

Regression pin: ``leaf_maps`` kept only the longest end per start, so a
``seq`` needing a shorter leaf alternative falsely failed. Shipped leaves
(lexicon longest-first, regex finditer) emit one end per start, so the
scenario needs a multi-end leaf — legal for community leaves via
``extra_grammars`` and the exact shape in the #73 acceptance criterion.
After the fix, ``seq`` depth-first branches over all ends per start
(bounded).
"""

from __future__ import annotations

import pytest

from paxman.core.grammar import AnchorSet
from paxman.core.grammar.matchers.combinator import CombinatorMatcher
from paxman.core.grammar.matchers.regex import RegexMatcher
from paxman.core.grammar.scan_context import ScanContext, View

pytestmark = pytest.mark.unit


class _TwoEndLeaf:
    """Stub leaf emitting two ends at start 0 (the #73 L3 premise)."""

    def match(self, view: View) -> list[tuple[int, int]]:
        return [(0, 1), (0, 2)] if view.subject.startswith("ab") else []


def _view(text: str) -> View:
    return ScanContext.of(text).view("__orig__", lambda t: (t, None, None))


def _seq(pattern: str, text: str) -> list[tuple[int, int]]:
    rx = RegexMatcher(pattern=pattern, boundary=None, view=None, anchors=AnchorSet())
    comb = CombinatorMatcher(expr=("seq", [_TwoEndLeaf(), rx]), view_name=None)
    return comb.match(_view(text))


def test_seq_uses_shorter_leaf_alternative() -> None:
    """seq(leaf{a,ab}, /b/) on 'ab' succeeds via (0,1) + 'b' (#73 L3)."""
    assert _seq(r"b", "ab") == [(0, 2)]


def test_seq_all_alternatives_miss() -> None:
    """seq(leaf{a,ab}, /c/) on 'ab' still yields no match."""
    assert _seq(r"c", "ab") == []


def test_seq_longest_alternative_preferred() -> None:
    """Longest-first order: seq on 'abb' takes (0,2) + 'b' → (0,3)."""
    assert _seq(r"b", "abb") == [(0, 3)]


def test_seq_backtracking_bounded() -> None:
    """Many-alternative leaf x 3-seq completes without blowup."""

    class _ManyEndLeaf:
        def match(self, view: View) -> list[tuple[int, int]]:
            n = len(view.subject)
            return [(0, i) for i in range(1, 21)] + [
                (21, i) for i in range(22, min(n + 1, 42))
            ]

    rx = RegexMatcher(pattern=r"b", boundary=None, view=None, anchors=AnchorSet())
    leaf = _ManyEndLeaf()
    comb = CombinatorMatcher(expr=("seq", [leaf, rx, leaf]), view_name=None)
    text = "a" * 20 + "b" + "a" * 20
    assert comb.match(_view(text)) == [(0, 41)]


def test_seq_budget_exhaustion_degrades_without_raising() -> None:
    """A tiny budget yields [] (never raises, never loops) (#73 L3)."""
    import paxman.core.grammar.matchers.combinator as comb_mod

    leaf = _TwoEndLeaf()
    rx = RegexMatcher(pattern=r"b", boundary=None, view=None, anchors=AnchorSet())
    view = _view("ab")
    leaf_maps = {id(leaf): {0: [2, 1]}, id(rx): {1: [2]}}
    assert comb_mod._eval_ends(("seq", [leaf, rx]), view, 0, leaf_maps, [0]) == []
    assert comb_mod._eval_ends(("seq", [leaf, rx]), view, 0, leaf_maps, [10000]) == [2]


def test_seq_opt_child_backtracks() -> None:
    """seq(opt(leaf), /b/) on 'ab' succeeds via take AND via skip."""
    leaf = _TwoEndLeaf()
    rx = RegexMatcher(pattern=r"b", boundary=None, view=None, anchors=AnchorSet())
    comb = CombinatorMatcher(expr=("seq", [("opt", leaf), rx]), view_name=None)
    assert comb.match(_view("ab")) == [(0, 2)]


def test_alt_is_ordered_choice() -> None:
    """alt commits to the first branch with ends (ordered choice)."""

    class _End2Leaf:
        def match(self, view: View) -> list[tuple[int, int]]:
            return [(0, 2)]

    class _End1Leaf:
        def match(self, view: View) -> list[tuple[int, int]]:
            return [(0, 1)]

    rx_b = RegexMatcher(pattern=r"b", boundary=None, view=None, anchors=AnchorSet())
    # Branch 1 yields (0,2); 'b' is not at 2, so seq fails even though
    # branch 2 offers (0,1) + 'b'. Concatenation would (wrongly) succeed.
    comb = CombinatorMatcher(
        expr=("seq", [("alt", [_End2Leaf(), _End1Leaf()]), rx_b]), view_name=None
    )
    assert comb.match(_view("ab")) == []
    # Reversed order: branch 1 (0,1) + 'b' succeeds → (0,2).
    comb2 = CombinatorMatcher(
        expr=("seq", [("alt", [_End1Leaf(), _End2Leaf()]), rx_b]), view_name=None
    )
    assert comb2.match(_view("ab")) == [(0, 2)]
