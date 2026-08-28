"""Trie-vs-alternation byte parity — both representations identical.

Keeps ~500-token auto-selection honest: LexiconMatcher with
trie vs alternation over same token set must emit identical spans.
Budget max_examples=200 deadline=None phases=[generate,target,shrink]
derandomize=False per-shard, cached examples.
"""

from __future__ import annotations

import string

import pytest
from hypothesis import HealthCheck, Phase, given, settings
from hypothesis import strategies as st

from paxman.capabilities.Country.grammar.data.chinese_names import CHINESE_NAME_KEYS
from paxman.capabilities.Country.grammar.data.english_names import ENGLISH_NAME_KEYS
from paxman.capabilities.Country.grammar.data.historical_names import (
    HISTORICAL_NAME_KEYS,
)
from paxman.capabilities.Country.grammar.data.localized_names import LOCALIZED_NAME_KEYS
from paxman.capabilities.SIUnit.grammar.data.unit_symbol_tokens import SYMBOL_TOKENS
from paxman.core.grammar import AnchorSet, BoundarySpec
from paxman.core.grammar.matchers.lexicon import LexiconMatcher
from paxman.core.grammar.scan_context import ScanContext

pytestmark = [pytest.mark.property]

_HYP_SETTINGS = settings(
    max_examples=200,
    deadline=None,
    phases=(Phase.generate, Phase.target, Phase.shrink),
    derandomize=False,
    suppress_health_check=list(HealthCheck),
)

_COUNTRY_TOKENS: frozenset[str] = frozenset(
    k.lower()
    for k in (
        ENGLISH_NAME_KEYS
        | HISTORICAL_NAME_KEYS
        | CHINESE_NAME_KEYS
        | LOCALIZED_NAME_KEYS
    )
)
_SYMBOL_TOKENS: frozenset[str] = frozenset(SYMBOL_TOKENS)
_SMALL_TOKENS: frozenset[str] = frozenset({"a", "ab", "abc", "US$", "€", "kg", "m"})


def _assert_trie_alt_parity(
    tokens: frozenset[str],
    boundary: BoundarySpec | None,
    view_name: str | None,
    text: str,
) -> None:
    trie = LexiconMatcher(
        tokens=tokens,
        boundary=boundary,
        view=view_name,
        anchors=AnchorSet(),
        representation="trie",
    )
    alt = LexiconMatcher(
        tokens=tokens,
        boundary=boundary,
        view=view_name,
        anchors=AnchorSet(),
        representation="alternation",
    )
    ctx = ScanContext.of(text)
    # resolve view same as engine_loop does
    from paxman.core.grammar.engine_loop import _resolve_view

    view = _resolve_view(ctx, view_name)
    assert trie.match(view) == alt.match(view)


_country_chars = "".join(sorted(set("".join(_COUNTRY_TOKENS)))) + " \t\n-/_.,"
_symbol_chars = "".join(sorted(set("".join(_SYMBOL_TOKENS)))) + " \t\n-/_.,·⋅°"


@st.composite
def _country_text(draw: st.DrawFn) -> str:
    # use single-word tokens to avoid longest-boundary interplay
    single_tokens = [t for t in sorted(_COUNTRY_TOKENS) if " " not in t]
    choice = draw(st.integers(min_value=0, max_value=1))
    if choice == 0:
        return draw(
            st.text(
                alphabet=_country_chars + string.ascii_letters, min_size=0, max_size=80
            )
        )
    tokens = draw(st.lists(st.sampled_from(single_tokens), min_size=0, max_size=3))
    sep = draw(st.sampled_from([" ", "  ", "\t", " - ", " / "]))
    core = sep.join(tokens)
    pad = draw(st.text(alphabet=_country_chars, min_size=0, max_size=6))
    return pad + core + pad


@st.composite
def _symbol_text(draw: st.DrawFn) -> str:
    choice = draw(st.integers(min_value=0, max_value=1))
    if choice == 0:
        return draw(st.text(alphabet=_symbol_chars, min_size=0, max_size=80))
    tokens = draw(
        st.lists(st.sampled_from(sorted(_SYMBOL_TOKENS)), min_size=0, max_size=3)
    )
    sep = draw(st.sampled_from([" ", "/", "·", "⋅", " ", "  "]))
    core = sep.join(tokens)
    pad = draw(st.text(alphabet=_symbol_chars, min_size=0, max_size=6))
    return pad + core + pad


_COUNTRY_SINGLE_TOKENS: frozenset[str] = frozenset(
    t for t in _COUNTRY_TOKENS if " " not in t
)


@_HYP_SETTINGS
@given(text=_country_text())
def test_country_trie_vs_alternation_parity(text: str) -> None:
    _assert_trie_alt_parity(_COUNTRY_SINGLE_TOKENS, BoundarySpec.WORD, None, text)


@_HYP_SETTINGS
@given(text=_symbol_text())
def test_siunit_symbol_trie_vs_alternation_parity(text: str) -> None:
    _assert_trie_alt_parity(_SYMBOL_TOKENS, BoundarySpec.DEGREE_WORD_SIGN, None, text)


@_HYP_SETTINGS
@given(
    text=st.text(
        alphabet=string.ascii_letters + string.digits + " _-.,\t\n",
        min_size=0,
        max_size=60,
    )
)
def test_small_token_trie_vs_alternation_parity(text: str) -> None:
    _assert_trie_alt_parity(_SMALL_TOKENS, BoundarySpec.WORD, None, text)


@_HYP_SETTINGS
@given(text=st.text(alphabet=string.ascii_letters + " \t\n", min_size=0, max_size=60))
def test_boundary_agnostic_trie_vs_alternation(text: str) -> None:
    # with WORD boundary, trie vs alt should match (word-anchored)
    tokens = frozenset({"hello", "world", "hell", "word"})
    _assert_trie_alt_parity(tokens, BoundarySpec.WORD, None, text)
