"""Parity shard — lexicon trie vs alternation byte-identical."""

import pytest

from paxman.capabilities.SIUnit.grammar.name_recognition import NameRecognition
from paxman.capabilities.SIUnit.grammar.symbol_recognition import SymbolRecognition
from tests.property._legacy_siunit_grammars import (
    LegacyNameRecognition,
    LegacySymbolRecognition,
)
from tests.property.grammar_kernel_parity import assert_kernel_parity

CURATED: list[str] = [
    "Pay US$ and $",
    "Buy € now",
    "US$ 1,000",
    "m/s and km",
    "United States treaty",
]

pytestmark = [pytest.mark.property]

# Reference helper to satisfy ruff F401 (import is part of the gate harness).
assert assert_kernel_parity is not None


@pytest.mark.property
@pytest.mark.parametrize(
    "text",
    [
        "Pay 5 m/s and 2 km now",
        "m/s and km",
        "k g",
        "KILOGRAM",
        "hello world",
        "degree celsius",
        "kilo gram",
        "x" * 430 + "kilogram" + "y" * 50,
    ],
)
def test_siunit_symbol_byte_identical(text: str) -> None:
    assert_kernel_parity(LegacySymbolRecognition(), SymbolRecognition(), text)


@pytest.mark.property
@pytest.mark.parametrize(
    "text",
    [
        "kilogram",
        "KILOGRAM",
        "degree celsius",
        "kilo gram",
        "hello world",
        "Pay 5 m/s and 2 km now",
        "x" * 430 + "kilogram" + "y" * 50,
    ],
)
def test_siunit_name_byte_identical(text: str) -> None:
    assert_kernel_parity(LegacyNameRecognition(), NameRecognition(), text)


@pytest.mark.property
def test_curated_corpus_parity_placeholder() -> None:
    pytest.skip(
        "Harness lands in Task 6; wire per-migration PR — "
        "no kind without its shard green."
    )
