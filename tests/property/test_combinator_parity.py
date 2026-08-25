"""Parity shard — combinator."""

import pytest

from paxman.core.grammar.matchers.combinator import CombinatorMatcher
from paxman.core.grammar.scan_context import ScanContext


@pytest.mark.property
def test_combinator_ordered_alt_placeholder() -> None:
    m = CombinatorMatcher(expr=("alt", [r"a", r"b"]))
    ctx = ScanContext.of("ab")
    view = ctx.view("orig", lambda t: (t, None))
    with pytest.raises(
        NotImplementedError, match="CombinatorMatcher not yet implemented"
    ):
        m.match(view)


@pytest.mark.property
def test_combinator_parity_placeholder() -> None:
    pytest.skip("Combinator parity harness — real Money/Date parity deferred")
