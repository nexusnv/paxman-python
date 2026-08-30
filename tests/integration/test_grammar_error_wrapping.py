"""Integration tests — grammar-path LookupError wraps as RecognitionError (#66).

A community grammar whose ``recognize()`` (legacy path) or compiled matcher
(engine-owned loop path) raises ``KeyError``/``IndexError`` must surface as
``RecognitionError`` from ``canonicalize()``, never as the raw exception.
"""

from __future__ import annotations

from collections.abc import Iterator

import pytest

from paxman.api.canonicalize import canonicalize
from paxman.capabilities.Date.capability import DateCapability
from paxman.capabilities.Date.contract import DateContract
from paxman.capabilities.Date.notation import DateNotation
from paxman.core.discovery import register_capability, reset_registry
from paxman.core.domain import Grammar, RecognitionMatch
from paxman.core.errors import RecognitionError
from paxman.core.extensions import register_grammar, reset_extensions
from paxman.core.grammar.scan_context import View


class ExplodingKeyGrammar(Grammar[DateNotation]):
    """Community grammar whose recognize() raises KeyError (data-bug shape)."""

    name = "exploding_key_recognition"
    semantics = "exploding_key_recognition"

    def recognize(self, text: str) -> list[RecognitionMatch[DateNotation]]:
        """Raise KeyError — the LookupError shape escaping the old tuple."""
        raise KeyError("missing token table entry")


class _ExplodingMatcher:
    """Matcher double whose match() raises IndexError (data-bug shape)."""

    def match(self, view: View) -> list[tuple[int, int]]:
        """Raise IndexError — the LookupError shape escaping the old tuple."""
        raise IndexError("offset map out of range")

    def emit(self, span: tuple[int, int], ctx: object) -> tuple[int, int]:
        """Return the span unchanged (never reached — match raises first)."""
        return span


class ExplodingMatcherGrammar(Grammar[DateNotation]):
    """Community grammar exposing a compiled matcher that raises IndexError."""

    name = "exploding_matcher_recognition"
    semantics = "exploding_matcher_recognition"
    matchers: list[object] = [_ExplodingMatcher()]

    def recognize(self, text: str) -> list[RecognitionMatch[DateNotation]]:
        """Return nothing — the engine loop path runs the matchers instead."""
        return []


@pytest.fixture(autouse=True)
def _clean_registry() -> Iterator[None]:
    """Reset capability and extension registries before every test."""
    reset_registry()
    reset_extensions()
    yield
    reset_registry()
    reset_extensions()


@pytest.fixture(autouse=True)
def _register_date_capability() -> Iterator[None]:
    """Register the Date capability for every test."""
    register_capability(DateCapability())
    yield


@pytest.mark.integration
def test_recognize_key_error_wraps_as_recognition_error() -> None:
    """(#66) A community grammar raising KeyError surfaces as RecognitionError."""
    register_grammar("date", ExplodingKeyGrammar)
    contract = DateContract(extra_grammars=("exploding_key_recognition",))
    with pytest.raises(RecognitionError):
        canonicalize("2024.01.01", contract)


@pytest.mark.integration
def test_matcher_index_error_wraps_as_recognition_error() -> None:
    """(#66) A community matcher raising IndexError surfaces as RecognitionError."""
    register_grammar("date", ExplodingMatcherGrammar)
    contract = DateContract(extra_grammars=("exploding_matcher_recognition",))
    with pytest.raises(RecognitionError) as excinfo:
        canonicalize("2024.01.01", contract)
    assert isinstance(excinfo.value.original_error, IndexError)


@pytest.mark.integration
def test_recognition_error_preserves_original() -> None:
    """(#66) The wrapped RecognitionError keeps the LookupError as original_error."""
    register_grammar("date", ExplodingKeyGrammar)
    contract = DateContract(extra_grammars=("exploding_key_recognition",))
    with pytest.raises(RecognitionError) as excinfo:
        canonicalize("2024.01.01", contract)
    assert isinstance(excinfo.value.original_error, KeyError)
    assert excinfo.value.rule == "exploding_key_recognition"
