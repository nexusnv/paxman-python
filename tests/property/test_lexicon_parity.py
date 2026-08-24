"""Parity shard — lexicon trie vs alternation byte-identical."""

import pytest

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
def test_curated_corpus_parity_placeholder() -> None:
    pytest.skip(
        "Harness lands in Task 6; wire per-migration PR — "
        "no kind without its shard green."
    )
