"""Tests for Element recognition grammar."""

import pytest

from paxman.capabilities.Element.grammar.data.element_keys import (
    NAME_KEYS,
    SYMBOL_KEYS,
)
from paxman.capabilities.Element.grammar.element_recognition import (
    ElementRecognitionGrammar,
)
from paxman.capabilities.Element.notation import ElementNotation
from paxman.core.domain import RecognitionMatch
from paxman.core.grammar import PipelineGrammar


def _recognize(text: str) -> list[RecognitionMatch[ElementNotation]]:
    return ElementRecognitionGrammar().recognize(text)


def _single(text: str) -> RecognitionMatch[ElementNotation]:
    matches = _recognize(text)
    assert len(matches) == 1, f"{text!r} -> {matches!r}"
    return matches[0]


@pytest.mark.capability
class TestElementRecognitionIdentity:
    """Grammar identity: name/semantics/single_value/matcher flags."""

    def test_name_and_semantics(self) -> None:
        grammar = ElementRecognitionGrammar()
        assert grammar.name == "element_recognition"
        assert grammar.semantics == "element_recognition"

    def test_single_value_true(self) -> None:
        assert ElementRecognitionGrammar().single_value is True

    def test_is_pipeline_grammar(self) -> None:
        assert isinstance(ElementRecognitionGrammar(), PipelineGrammar)

    def test_empty_guard_pre(self) -> None:
        pre = ElementRecognitionGrammar.pre
        assert pre is not None
        assert pre.empty_guard is True

    def test_matcher_count_and_order(self) -> None:
        matchers = ElementRecognitionGrammar.matchers
        assert matchers is not None
        assert len(matchers) == 3
        assert matchers[0].kind == "regex"
        assert matchers[1].kind == "lexicon"
        assert matchers[2].kind == "lexicon"

    def test_matcher_suppressible_flags(self) -> None:
        matchers = ElementRecognitionGrammar.matchers
        assert matchers is not None
        z_matcher, symbol_matcher, name_matcher = matchers
        assert z_matcher.suppressible is False
        assert symbol_matcher.suppressible is True
        assert name_matcher.suppressible is False


@pytest.mark.capability
class TestSymbolRecognition:
    """Case-exact symbol branch: canonical + lowercase fold, no all-caps."""

    @pytest.mark.parametrize(
        ("text", "token"),
        [("Fe", "Fe"), ("fe", "Fe"), ("C", "C"), ("Og", "Og")],
    )
    def test_symbol_shapes(self, text: str, token: str) -> None:
        match = _single(text)
        assert match.notation == ElementNotation(token=token, shape="symbol")
        assert (match.start, match.end) == (0, len(text))
        assert match.raw_text == text


@pytest.mark.capability
class TestNameRecognition:
    """Case-insensitive name branch: emit lowercases the raw span."""

    @pytest.mark.parametrize(
        ("text", "token"),
        [
            ("iron", "iron"),
            ("Iron", "iron"),
            ("IRON", "iron"),
            ("aluminium", "aluminium"),
            ("aluminum", "aluminum"),
            ("caesium", "caesium"),
            ("cesium", "cesium"),
        ],
    )
    def test_name_shapes(self, text: str, token: str) -> None:
        match = _single(text)
        assert match.notation == ElementNotation(token=token, shape="name")
        assert (match.start, match.end) == (0, len(text))
        assert match.raw_text == text


@pytest.mark.capability
class TestAtomicNumberRecognition:
    """Label-required Z branch: span includes the label, notation digits-only."""

    @pytest.mark.parametrize(
        ("text", "token"),
        [
            ("element 26", "26"),
            ("Z=26", "26"),
            ("Z = 92", "92"),
            ("atomic number 118", "118"),
            ("element 026", "26"),
        ],
    )
    def test_z_shapes(self, text: str, token: str) -> None:
        match = _single(text)
        assert match.notation == ElementNotation(token=token, shape="atomic_number")
        assert (match.start, match.end) == (0, len(text))
        assert match.raw_text == text


@pytest.mark.capability
class TestRecognitionNegatives:
    """Boundary/label negatives: no claim (empty match list)."""

    @pytest.mark.parametrize(
        "text",
        [
            "irony",
            "Fe2O3",
            "NaCl",
            "56Fe",
            "Fe-56",
            "element26",
            "Z26",
            "FE",
            "fE",
            "Xx",
            "Uut",
            "element 1000",
            "element ٢٦",  # non-ASCII digits never claimed ([0-9] is ASCII-only)
            "",
            "   ",
        ],
    )
    def test_no_match(self, text: str) -> None:
        assert _recognize(text) == []


@pytest.mark.capability
class TestSpanInvariants:
    """Every emitted match is span-bearing over the input text."""

    @pytest.mark.parametrize(
        "text",
        [
            "Fe",
            "fe",
            "C",
            "Og",
            "iron",
            "Iron",
            "aluminium",
            "element 26",
            "Z=26",
            "Z = 92",
            "atomic number 118",
        ],
    )
    def test_span_invariants(self, text: str) -> None:
        for match in _recognize(text):
            assert 0 <= match.start < match.end <= len(text)
            assert match.raw_text == text[match.start : match.end]


@pytest.mark.capability
class TestElementKeys:
    """Grammar key tables: sizes, no all-caps symbols, no retired keys."""

    def test_key_set_sizes(self) -> None:
        assert len(SYMBOL_KEYS) == 236
        assert len(NAME_KEYS) == 120

    def test_no_allcaps_symbol_keys(self) -> None:
        assert "FE" not in SYMBOL_KEYS
        assert "NO" not in SYMBOL_KEYS
        assert "IN" not in SYMBOL_KEYS

    def test_no_retired_keys(self) -> None:
        assert "Uut" not in SYMBOL_KEYS
        assert "ununtrium" not in NAME_KEYS
        assert "sulphur" not in NAME_KEYS
