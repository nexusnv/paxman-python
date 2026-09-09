"""Hypothesis property tests for the Element capability.

Each property locks a mathematical invariant using an independently derived
expectation:

- every sampled symbol key is recognized exactly once and validated by the
  Red Book rule to itself (grammar/rule direct drive — no registry);
- every sampled name key is recognized exactly once and validated by the
  Red Book rule to its registry symbol (direct drive);
- every sampled atomic number is recognized exactly once from its labeled
  form and validated by the registry rule (direct drive);
- sampled symbols, names, and atomic numbers self-canonicalize through the
  full pipeline (canonical values are fixed points);
- the iron family (``fe``/``Fe``/``iron``/``IRON``/``element 26``) resolves
  to one value;
- ``format_value`` is the identity for ``symbol`` and the IUPAC-spelling
  lookup for ``name``;
- random ASCII input never raises (besides ``MultipleMentionsError``) and
  ``INVALID`` arises only via the label branch (symbol/name shapes always
  validate — Task 9 consistency);
- the MILESTONE row-22 vectors hold verbatim.

Registry posture: grammar/rule/``format_value`` properties drive those
layers directly and never touch the registry. Full-pipeline properties
(self-canonicalization, equivalence, fuzz, MILESTONE vectors) use a local
``_fresh_registry`` fixture registering only Element — the documented
``test_money_properties.py`` exception pattern (pipeline invariants cannot
be observed off-pipeline).
"""

from __future__ import annotations

import re
import string

import pytest
from hypothesis import given
from hypothesis import strategies as st

from paxman.capabilities.Element.capability import ElementCapability
from paxman.capabilities.Element.contract import ElementContract
from paxman.capabilities.Element.grammar.element_recognition import (
    ElementRecognitionGrammar,
)
from paxman.capabilities.Element.notation import ElementNotation
from paxman.capabilities.Element.rules.data.periodic_table_ed2022 import (
    NAME_TO_SYMBOL,
    SYMBOL_TO_NAME,
    SYMBOLS,
    Z_TO_SYMBOL,
)
from paxman.capabilities.Element.rules.iupac_periodic_table_ed2022 import (
    SectionPtoeRegistry,
)
from paxman.capabilities.Element.rules.iupac_red_book_2005 import (
    SectionIR31NamesAndSymbols,
)
from paxman.core.discovery import register_capability, reset_registry
from paxman.core.domain import Resolution
from paxman.core.errors import MultipleMentionsError
from paxman.engine.orchestrator import run_capability

pytestmark = pytest.mark.property

_LABEL_PRESENT = re.compile(r"(?i:(?:element|atomic number|Z)[\s:=]+[0-9]{1,3})")

_MILESTONE_VECTORS: tuple[tuple[str, str], ...] = (
    ("Iron", "Fe"),
    ("fe", "Fe"),
    ("Gold", "Au"),
    ("Al", "Al"),
    ("Carbon", "C"),
    ("element 118", "Og"),
    ("Z = 92", "U"),
    ("atomic number 79", "Au"),
)


@pytest.fixture(autouse=True)
def _fresh_registry() -> None:
    """Reset the registry and register Element before and after each test.

    Registration happens once per test, before the hypothesis examples run;
    ``run_capability`` freezes the registry on the first example, which is
    fine because the capability is already present.
    """
    reset_registry()
    register_capability(ElementCapability())
    yield
    reset_registry()


@given(s=st.sampled_from(sorted(SYMBOLS)))
def test_symbol_key_recognized_and_validated(s: str) -> None:
    """Every registry symbol is recognized once and validates to itself."""
    matches = ElementRecognitionGrammar().recognize(s)
    assert len(matches) == 1
    assert matches[0].notation.shape == "symbol"
    assert matches[0].notation.token == s
    rule = SectionIR31NamesAndSymbols()
    assert rule.matches(matches[0].notation, ElementContract()) is True
    assert rule.normalize(matches[0].notation, ElementContract()) == s


@given(n=st.sampled_from(sorted(NAME_TO_SYMBOL)))
def test_name_key_recognized_and_validated(n: str) -> None:
    """Every registry name is recognized once and validates to its symbol."""
    matches = ElementRecognitionGrammar().recognize(n)
    assert len(matches) == 1
    assert matches[0].notation.shape == "name"
    assert matches[0].notation.token == n
    rule = SectionIR31NamesAndSymbols()
    assert rule.matches(matches[0].notation, ElementContract()) is True
    assert rule.normalize(matches[0].notation, ElementContract()) == (NAME_TO_SYMBOL[n])


@given(z=st.integers(min_value=1, max_value=118))
def test_z_label_recognized_and_validated(z: int) -> None:
    """Every atomic number is recognized once from its labeled form."""
    matches = ElementRecognitionGrammar().recognize(f"element {z}")
    assert len(matches) == 1
    assert matches[0].notation.shape == "atomic_number"
    assert matches[0].notation.token == str(z)
    rule = SectionPtoeRegistry()
    assert rule.matches(matches[0].notation, ElementContract()) is True
    assert rule.normalize(matches[0].notation, ElementContract()) == Z_TO_SYMBOL[z]


@given(s=st.sampled_from(sorted(SYMBOLS)))
def test_sampled_symbol_self_canonicalizes(s: str) -> None:
    """A canonical symbol re-canonicalizes to itself (fixed point)."""
    contract = ElementCapability.create_contract()
    result = run_capability(s, contract)
    assert result.status is Resolution.SUCCESS
    assert result.canonicalized_value == s


@given(n=st.sampled_from(sorted(NAME_TO_SYMBOL)))
def test_sampled_name_self_canonicalizes(n: str) -> None:
    """A registry name canonicalizes to its symbol, which is a fixed point."""
    contract = ElementCapability.create_contract()
    result = run_capability(n, contract)
    assert result.status is Resolution.SUCCESS
    assert result.canonicalized_value == NAME_TO_SYMBOL[n]
    again = run_capability(NAME_TO_SYMBOL[n], contract)
    assert again.status is Resolution.SUCCESS
    assert again.canonicalized_value == NAME_TO_SYMBOL[n]


@given(z=st.integers(min_value=1, max_value=118))
def test_sampled_z_self_canonicalizes(z: int) -> None:
    """A labeled atomic number canonicalizes to its symbol (a fixed point)."""
    contract = ElementCapability.create_contract()
    result = run_capability(f"element {z}", contract)
    assert result.status is Resolution.SUCCESS
    assert result.canonicalized_value == Z_TO_SYMBOL[z]
    again = run_capability(Z_TO_SYMBOL[z], contract)
    assert again.status is Resolution.SUCCESS
    assert again.canonicalized_value == Z_TO_SYMBOL[z]


def test_iron_family_equivalence() -> None:
    """Symbol, folded symbol, name, upper name, and label share one value."""
    contract = ElementCapability.create_contract()
    values = {
        run_capability(text, contract).canonicalized_value
        for text in ("fe", "Fe", "iron", "IRON", "element 26")
    }
    assert values == {"Fe"}


@given(s=st.sampled_from(sorted(SYMBOLS)))
def test_format_value_symbol_identity(s: str) -> None:
    """The ``symbol`` format renders the canonical value unchanged."""
    capability = ElementCapability()
    notation = ElementNotation(token=s, shape="symbol")
    assert capability.format_value(s, "symbol", notation) == s


@given(s=st.sampled_from(sorted(SYMBOLS)))
def test_format_value_name_lookup(s: str) -> None:
    """The ``name`` format renders the IUPAC spelling (never an alias)."""
    capability = ElementCapability()
    notation = ElementNotation(token=s, shape="symbol")
    assert capability.format_value(s, "name", notation) == SYMBOL_TO_NAME[s]


@given(text=st.text(alphabet=string.printable, max_size=40))
def test_random_ascii_status_well_formed(text: str) -> None:
    """Random ASCII never raises and INVALID arrives only via the label.

    Symbol/name recognitions always validate (Task 9 consistency), so an
    INVALID outcome proves the label branch claimed an out-of-range number
    alone — the label text must be present in the input.
    """
    contract = ElementCapability.create_contract()
    try:
        result = run_capability(text, contract)
    except MultipleMentionsError:
        return
    assert result.status in (
        Resolution.SUCCESS,
        Resolution.MISSING,
        Resolution.INVALID,
        Resolution.AMBIGUOUS,
    )
    if result.status is Resolution.INVALID:
        assert _LABEL_PRESENT.search(text) is not None
    if result.status in (Resolution.MISSING, Resolution.INVALID):
        assert result.candidates == ()


@pytest.mark.parametrize(("text", "expected"), _MILESTONE_VECTORS)
def test_milestone_vectors(text: str, expected: str) -> None:
    """MILESTONE row-22 vectors hold verbatim through the pipeline."""
    contract = ElementCapability.create_contract()
    result = run_capability(text, contract)
    assert result.status is Resolution.SUCCESS
    assert result.canonicalized_value == expected
