"""Parity shard — combinator (ADR §9.4)."""

from __future__ import annotations

import hashlib

import pytest

from paxman.capabilities.SIUnit.grammar.data.prefix_tokens import PREFIX_SYMBOL_TOKENS
from paxman.capabilities.SIUnit.grammar.data.unit_symbol_tokens import SYMBOL_TOKENS
from paxman.capabilities.SIUnit.grammar.symbol_recognition import SymbolRecognition
from paxman.core.grammar import AnchorSet, BoundarySpec
from paxman.core.grammar.matchers.combinator import CombinatorMatcher
from paxman.core.grammar.matchers.lexicon import LexiconMatcher
from paxman.core.grammar.matchers.regex import RegexMatcher
from paxman.core.grammar.scan_context import ScanContext
from tests.property._legacy_siunit_grammars import LegacySymbolRecognition
from tests.property.grammar_kernel_parity import assert_kernel_parity

pytestmark = [pytest.mark.property]

DUAL = frozenset({"a", "d", "h", "m"})
PREFIX_ONLY = frozenset(PREFIX_SYMBOL_TOKENS) - DUAL


def test_combinator_seq_basic() -> None:
    prefix = LexiconMatcher(
        tokens=PREFIX_ONLY,
        boundary=None,
        view=None,
        anchors=AnchorSet(),
        representation="auto",
    )
    unit = LexiconMatcher(
        tokens=frozenset(SYMBOL_TOKENS),
        boundary=None,
        view=None,
        anchors=AnchorSet(),
        representation="auto",
    )
    ws = RegexMatcher(pattern=" ", boundary=None, view=None, anchors=AnchorSet())
    comb = CombinatorMatcher(
        expr=("seq", [prefix, ws, unit]),
        view_name=None,
        boundary=BoundarySpec.DEGREE_WORD_SIGN,
    )
    ctx = ScanContext.of("k g")
    view = ctx.view("__orig__", lambda t: (t, None, None))
    assert comb.match(view) == [(0, 3)]


def test_combinator_alt_ordered_first_wins() -> None:
    a = RegexMatcher(pattern="a", boundary=None, view=None, anchors=AnchorSet())
    b = RegexMatcher(pattern="a", boundary=None, view=None, anchors=AnchorSet())
    comb = CombinatorMatcher(expr=("alt", [a, b]), view_name=None)
    ctx = ScanContext.of("a")
    view = ctx.view("__orig__", lambda t: (t, None, None))
    assert comb.match(view) == [(0, 1)]
    # alt with distinct branches
    c = RegexMatcher(pattern="b", boundary=None, view=None, anchors=AnchorSet())
    comb2 = CombinatorMatcher(expr=("alt", [c, a]), view_name=None)
    ctx2 = ScanContext.of("a")
    view2 = ctx2.view("__orig__", lambda t: (t, None, None))
    assert comb2.match(view2) == [(0, 1)]


def test_combinator_opt() -> None:
    x = RegexMatcher(pattern="x", boundary=None, view=None, anchors=AnchorSet())
    comb = CombinatorMatcher(expr=("opt", x), view_name=None)
    ctx = ScanContext.of("y")
    view = ctx.view("__orig__", lambda t: (t, None, None))
    # opt at top-level should not emit zero-length
    assert comb.match(view) == []
    # opt inside seq should allow missing
    y = RegexMatcher(pattern="y", boundary=None, view=None, anchors=AnchorSet())
    comb2 = CombinatorMatcher(expr=("seq", [("opt", x), y]), view_name=None)
    ctx2 = ScanContext.of("y")
    view2 = ctx2.view("__orig__", lambda t: (t, None, None))
    assert comb2.match(view2) == [(0, 1)]


def test_combinator_rep() -> None:
    a = RegexMatcher(pattern="a", boundary=None, view=None, anchors=AnchorSet())
    comb = CombinatorMatcher(expr=("rep", a), view_name=None)
    ctx = ScanContext.of("aaa")
    view = ctx.view("__orig__", lambda t: (t, None, None))
    assert comb.match(view) == [(0, 3)]
    comb_min = CombinatorMatcher(expr=("rep", a, 2), view_name=None)
    ctx2 = ScanContext.of("a")
    view2 = ctx2.view("__orig__", lambda t: (t, None, None))
    assert comb_min.match(view2) == []


def test_combinator_label() -> None:
    b = RegexMatcher(pattern="b", boundary=None, view=None, anchors=AnchorSet())
    comb = CombinatorMatcher(expr=("label", "my", b), view_name=None)
    ctx = ScanContext.of("b")
    view = ctx.view("__orig__", lambda t: (t, None, None))
    assert comb.match(view) == [(0, 1)]


@pytest.mark.parametrize(
    "text",
    [
        "k g",
        "M Hz",
        "da m",
        "µ g",
        "k g and M Hz",
        "m s",
        " x k g y ",
        "da m/s",
        "k gextra",
        "hello world",
        "m/s and km",
        "kg m/s²",
    ],
)
def test_siunit_split_parity_byte_identical(text: str) -> None:
    assert_kernel_parity(LegacySymbolRecognition(), SymbolRecognition(), text)


def test_freeze_digest_shrinks() -> None:
    from paxman.capabilities.SIUnit.grammar.symbol_recognition import _ALL_SYMBOL_TOKENS

    assert len(_ALL_SYMBOL_TOKENS) == 930
    # product inflated size was 19530
    old_product = 19530
    assert len(_ALL_SYMBOL_TOKENS) < old_product
    assert len(_ALL_SYMBOL_TOKENS) == 930
    # digest over 930 cheaper than over 19530: hash of sorted tokens
    old_tokens = frozenset(SYMBOL_TOKENS) | frozenset(
        f"{p} {s}" for p in PREFIX_ONLY for s in SYMBOL_TOKENS
    )
    assert len(old_tokens) == 19530
    old_digest = hashlib.sha256("\x00".join(sorted(old_tokens)).encode()).hexdigest()
    new_digest = hashlib.sha256(
        "\x00".join(sorted(_ALL_SYMBOL_TOKENS)).encode()
    ).hexdigest()
    assert old_digest != new_digest
    assert len(_ALL_SYMBOL_TOKENS) == 930
