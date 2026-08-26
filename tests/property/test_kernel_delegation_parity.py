"""Gating parity: PipelineGrammar.recognize delegates to engine loop (A7).

Two invariants:
- g.recognize(text) == run_matchers(text, [g]) for migrated grammars.
- Mutating g.matchers changes recognize output (proves delegation live, not dead body).
"""

from __future__ import annotations

from typing import Any

import pytest

from paxman.capabilities.Country.grammar.name_recognition import NameGrammar
from paxman.capabilities.Country.notation import CountryNotation
from paxman.capabilities.SIUnit.grammar.name_recognition import NameRecognition
from paxman.capabilities.SIUnit.grammar.symbol_recognition import SymbolRecognition
from paxman.capabilities.SIUnit.notation import SIUnitNotation
from paxman.core.grammar import AnchorSet, BoundarySpec
from paxman.core.grammar.engine_loop import run_matchers
from paxman.core.grammar.matchers.lexicon import LexiconMatcher
from paxman.core.grammar.scan_context import ScanContext

pytestmark = [pytest.mark.property]


def _assert_delegation(g: Any, text: str) -> None:
    out_via_recognize = g.recognize(text)  # type: ignore[operator]
    out_via_engine = run_matchers(text, [g])  # type: ignore[arg-type]
    assert out_via_recognize == out_via_engine, (
        f"delegation mismatch for {type(g).__name__!r} text={text!r}: "
        f"recognize={out_via_recognize!r} vs run_matchers={out_via_engine!r}"
    )


CORPUS: list[str] = [
    "United States",
    "canada",
    "  united states  ",
    "Alemania",
    "Burma",
    "中国",
    "840",
    "XYZ",
    "",
    "   ",
    "U.S.A.",
    "Guinea-Bissau",
    "France, Metropolitan",
    "kg",
    "MHz",
    "k g",
    "Kilogram",
    "KILOGRAM",
    "degree celsius",
    "kilo gram",
    "m/s",
    "m/s²",
    "25°C",
    "hello world",
]


@pytest.mark.parametrize("text", CORPUS)
def test_delegation_parity_country_name(text: str) -> None:
    g = NameGrammar()
    _assert_delegation(g, text)


@pytest.mark.parametrize(
    "text",
    ["kg", "MHz", "k g", "KILOGRAM", "hello", "m/s", "kPa", "°C", "", "k g"],
)
def test_delegation_parity_siunit_symbol(text: str) -> None:
    g = SymbolRecognition()
    _assert_delegation(g, text)


@pytest.mark.parametrize(
    "text",
    [
        "kilogram",
        "Kilogram",
        "KILOGRAM",
        "degree celsius",
        "kilo gram",
        "hello",
        "kg",
        "",
    ],
)
def test_delegation_parity_siunit_name(text: str) -> None:
    g = NameRecognition()
    _assert_delegation(g, text)


def _country_emit(span: tuple[int, int], ctx: ScanContext) -> CountryNotation:
    s, e = span
    raw = ctx.text[s:e]
    return CountryNotation(shape="name", value=raw)


def _si_emit(span: tuple[int, int], ctx: ScanContext) -> SIUnitNotation:
    s, e = span
    token = ctx.text[s:e]
    return SIUnitNotation(text=token, shape="symbol")


def test_mutate_matcher_country_proves_delegation() -> None:
    g = NameGrammar()
    # baseline: recognizes a known name
    assert len(g.recognize("United States")) == 1
    # mutate matchers to a token not in original lexicon
    fake = LexiconMatcher(
        tokens=frozenset({"xyzzymutatetoken"}),
        boundary=BoundarySpec.WORD,
        view="country_normalized",
        anchors=AnchorSet(),
        emit=_country_emit,
    )
    # Patch instance attribute — delegation reads self.matchers
    object.__setattr__(g, "matchers", (fake,))  # PipelineGrammar.matchers is ClassVar
    # After delegation, old token must disappear, new token must appear
    assert g.recognize("United States") == []  # mutation not reflected
    out = g.recognize("xyzzymutatetoken")
    assert len(out) == 1
    assert out[0].raw_text == "xyzzymutatetoken"


def test_mutate_matcher_si_symbol_proves_delegation() -> None:
    g = SymbolRecognition()
    assert len(g.recognize("kg")) == 1
    fake = LexiconMatcher(
        tokens=frozenset({"xyzzysymbol"}),
        boundary=BoundarySpec.DEGREE_WORD_SIGN,
        view=None,
        anchors=AnchorSet(),
        emit=_si_emit,
    )
    object.__setattr__(g, "matchers", (fake,))
    assert g.recognize("kg") == [], "mutation not reflected — delegation dead"
    out = g.recognize("xyzzysymbol")
    assert len(out) == 1
    assert out[0].raw_text == "xyzzysymbol"
