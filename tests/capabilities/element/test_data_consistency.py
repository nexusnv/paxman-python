"""Authority-table consistency for the Element capability.

The IUPAC Periodic Table of the Elements (04 May 2022) snapshot backs both
validation rules: every recognized symbol, name, and atomic number must
resolve through these tables to a canonical proper-case IUPAC symbol.
"""

from __future__ import annotations

import pytest

from paxman.capabilities.Element.grammar.data import element_keys
from paxman.capabilities.Element.grammar.data.element_keys import (
    NAME_KEYS,
    SYMBOL_KEYS,
)
from paxman.capabilities.Element.rules.data.periodic_table_ed2022 import (
    NAME_TO_SYMBOL,
    SYMBOL_TO_NAME,
    SYMBOLS,
    Z_TO_SYMBOL,
)

pytestmark = pytest.mark.capability


class TestRegistryCounts:
    def test_registry_counts(self) -> None:
        assert len(SYMBOLS) == 118
        assert len(NAME_TO_SYMBOL) == 120
        assert len(Z_TO_SYMBOL) == 118
        assert len(SYMBOL_TO_NAME) == 118


class TestAliasesResolveToCanonical:
    def test_aliases_resolve_to_canonical(self) -> None:
        assert NAME_TO_SYMBOL["aluminum"] == "Al"
        assert NAME_TO_SYMBOL["cesium"] == "Cs"
        assert NAME_TO_SYMBOL["aluminium"] == "Al"
        assert NAME_TO_SYMBOL["caesium"] == "Cs"


class TestZBoundaries:
    def test_z_boundaries(self) -> None:
        assert Z_TO_SYMBOL[1] == "H"
        assert Z_TO_SYMBOL[118] == "Og"
        assert 0 not in Z_TO_SYMBOL
        assert 119 not in Z_TO_SYMBOL


class TestSymbolNameZBijection:
    def test_symbol_name_z_bijection(self) -> None:
        assert set(Z_TO_SYMBOL.values()) == set(SYMBOLS)
        assert set(SYMBOL_TO_NAME) == set(SYMBOLS)
        assert set(NAME_TO_SYMBOL.values()) == set(SYMBOLS)
        for z, symbol in Z_TO_SYMBOL.items():
            assert NAME_TO_SYMBOL[SYMBOL_TO_NAME[symbol]] == symbol
            assert Z_TO_SYMBOL[z] == symbol
        assert len(set(SYMBOL_TO_NAME.values())) == 118


class TestEverySymbolKeyInSymbols:
    def test_every_symbol_key_in_symbols(self) -> None:
        """Every lexicon symbol key folds (emit idiom) to a known symbol."""
        folded = {key[0].upper() + key[1:].lower() for key in SYMBOL_KEYS}
        assert folded == set(SYMBOLS)

    def test_symbol_keys_cover_both_cases_per_symbol(self) -> None:
        """Each symbol contributes exactly its canonical + lowercase keys."""
        assert len(SYMBOL_KEYS) == 2 * len(SYMBOLS)
        for symbol in SYMBOLS:
            assert symbol in SYMBOL_KEYS
            assert symbol.lower() in SYMBOL_KEYS


class TestEveryNameKeyInNameMap:
    def test_every_name_key_in_name_map(self) -> None:
        """Every lexicon name key resolves through the rule-side name map."""
        assert set(NAME_KEYS) <= set(NAME_TO_SYMBOL)

    def test_name_map_covered_by_name_keys(self) -> None:
        """Every rule-side name is reachable from some grammar key."""
        assert set(NAME_TO_SYMBOL) <= set(NAME_KEYS)


class TestEveryZInRangeRecognizable:
    def test_every_z_in_range_recognizable(self) -> None:
        """Rule-side coverage for Z 1–118 (the label branch is generative).

        The atomic-number grammar branch is a label-required regex matching
        any 1–3 digit core, so per-key grammar assertions are vacuous;
        what must hold is that every in-range integer resolves in the
        registry snapshot backing the rule.
        """
        assert set(Z_TO_SYMBOL) == set(range(1, 119))


class TestNoGrammarKeyMapsToCanonical:
    def test_no_grammar_key_maps_to_canonical(self) -> None:
        """Grammar tables are key-only: no token-to-symbol mappings.

        Boundary audit for the grammar/rule split — canonical decisions
        live in ``rules/data/`` alone.
        """
        for name, value in vars(element_keys).items():
            if not name.isupper():
                continue
            assert isinstance(value, frozenset), name
            assert all(isinstance(key, str) for key in value), name
