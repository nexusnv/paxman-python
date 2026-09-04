"""Integration tests for the Element capability through the full pipeline."""

from __future__ import annotations

from collections.abc import Iterator

import pytest

from paxman.capabilities.Element.capability import ElementCapability
from paxman.core.discovery import register_capability, reset_registry
from paxman.core.domain import Resolution
from paxman.core.errors import MultipleMentionsError
from paxman.engine.orchestrator import run_capability

_RED_BOOK_RULE = "Section IR-3.1-names-and-symbols"
_REGISTRY_RULE = "Section PTOE-element-registry"


@pytest.fixture(autouse=True)
def _clean_registry() -> Iterator[None]:
    """Reset the capability registry before and after each test."""
    reset_registry()
    yield
    reset_registry()


class TestElementPipeline:
    """End-to-end tests for Element canonicalization.

    Locked semantics (plan §9 as amended by A0):
    - symbols are case-exact (``fe`` folds, ``FE`` stays unclaimed);
    - names match case-insensitively (``IRON`` resolves);
    - atomic numbers require a label (bare ``26`` is unclaimable);
    - recognized-but-unknown designations are INVALID only via the label
      branch (``element 119``); everything else unclaimed is MISSING;
    - two distinct values in one call raise ``MultipleMentionsError``;
    - co-referent mentions (``Iron (Fe)``) coalesce to one SUCCESS.
    """

    @pytest.mark.integration
    @pytest.mark.parametrize(
        ("text", "expected_value", "expected_rule", "expected_span"),
        [
            ("Fe", "Fe", _RED_BOOK_RULE, (0, 2)),
            ("IRON", "Fe", _RED_BOOK_RULE, (0, 4)),
            ("aluminum", "Al", _RED_BOOK_RULE, (0, 8)),
            ("element 026", "Fe", _REGISTRY_RULE, (0, 11)),
            ("Z = 26", "Fe", _REGISTRY_RULE, (0, 6)),
        ],
    )
    def test_success_rows(
        self,
        text: str,
        expected_value: str,
        expected_rule: str,
        expected_span: tuple[int, int],
    ) -> None:
        """Symbol, name, and labeled-atomic-number inputs canonicalize."""
        register_capability(ElementCapability())
        contract = ElementCapability.create_contract()
        result = run_capability(text, contract)

        assert result.status == Resolution.SUCCESS
        assert result.canonicalized_value == expected_value
        assert result.span == expected_span
        assert len(result.candidates) >= 1
        assert {c.value for c in result.candidates} == {expected_value}
        for candidate in result.candidates:
            assert candidate.validation_rule == expected_rule
            assert candidate.provenance[0].authority == "IUPAC"

    @pytest.mark.integration
    def test_unknown_symbol_is_missing(self) -> None:
        """Unclaimed symbol-like input is MISSING, not INVALID."""
        register_capability(ElementCapability())
        contract = ElementCapability.create_contract()
        result = run_capability("Xx", contract)

        assert result.status == Resolution.MISSING
        assert result.canonicalized_value is None
        assert result.candidates == ()

    @pytest.mark.integration
    @pytest.mark.parametrize("text", ["element 119", "Z = 300"])
    def test_out_of_range_atomic_number_is_invalid(self, text: str) -> None:
        """A labeled but out-of-range atomic number is INVALID."""
        register_capability(ElementCapability())
        contract = ElementCapability.create_contract()
        result = run_capability(text, contract)

        assert result.status == Resolution.INVALID
        assert result.canonicalized_value is None
        assert result.candidates == ()

    @pytest.mark.integration
    @pytest.mark.parametrize("text", ["hello world", "26", "FE", "Fe-56", "ununtrium"])
    def test_missing_rows(self, text: str) -> None:
        """Unclaimable inputs are MISSING.

        ``hello world`` holds no element token; bare ``26`` needs a label;
        ``FE`` is all-caps (no all-caps keys); ``Fe-56`` is isotope-glued;
        ``ununtrium`` is a retired systematic name with no key.
        """
        register_capability(ElementCapability())
        contract = ElementCapability.create_contract()
        result = run_capability(text, contract)

        assert result.status == Resolution.MISSING
        assert result.canonicalized_value is None
        assert result.candidates == ()

    @pytest.mark.integration
    def test_two_distinct_elements_raise(self) -> None:
        """Two distinct values in one call fail fast, not AMBIGUOUS."""
        register_capability(ElementCapability())
        contract = ElementCapability.create_contract()
        with pytest.raises(MultipleMentionsError):
            run_capability("Fe and Cu", contract)

    @pytest.mark.integration
    def test_coreferent_symbol_and_name_coalesce(self) -> None:
        """``Iron (Fe)`` is one entity: both mentions resolve to ``Fe``."""
        register_capability(ElementCapability())
        contract = ElementCapability.create_contract()
        result = run_capability("Iron (Fe)", contract)

        assert result.status == Resolution.SUCCESS
        assert result.canonicalized_value == "Fe"
        assert result.span == (0, 4)
        assert {c.value for c in result.candidates} == {"Fe"}
        for candidate in result.candidates:
            assert candidate.validation_rule == _RED_BOOK_RULE
            assert candidate.provenance[0].authority == "IUPAC"

    @pytest.mark.integration
    def test_coreferent_label_and_name_coalesce(self) -> None:
        """``element 26 (iron)`` resolves through both rules to ``Fe``."""
        register_capability(ElementCapability())
        contract = ElementCapability.create_contract()
        result = run_capability("element 26 (iron)", contract)

        assert result.status == Resolution.SUCCESS
        assert result.canonicalized_value == "Fe"
        assert result.span == (0, 10)
        assert {c.value for c in result.candidates} == {"Fe"}
        assert {c.validation_rule for c in result.candidates} == {
            _RED_BOOK_RULE,
            _REGISTRY_RULE,
        }

    @pytest.mark.integration
    def test_common_word_symbol_flag_off(self) -> None:
        """``in`` resolves to ``In`` when suppression is off."""
        register_capability(ElementCapability())
        contract = ElementCapability.create_contract(suppress_common_words=False)
        result = run_capability("in", contract)

        assert result.status == Resolution.SUCCESS
        assert result.canonicalized_value == "In"
        assert result.span == (0, 2)
        assert result.suppressed_count == 0
        assert result.suppressed_spans == ()

    @pytest.mark.integration
    def test_common_word_symbol_whole_input_exempt(self) -> None:
        """Whole-input ``in`` stays SUCCESS with the flag on (A0 exempt)."""
        register_capability(ElementCapability())
        contract = ElementCapability.create_contract(suppress_common_words=True)
        result = run_capability("in", contract)

        assert result.status == Resolution.SUCCESS
        assert result.canonicalized_value == "In"
        assert result.suppressed_count == 0
        assert result.suppressed_spans == ()

    @pytest.mark.integration
    def test_embedded_common_word_symbol_suppressed(self) -> None:
        """Embedded ``in`` is suppressed; ``Fe`` still resolves."""
        register_capability(ElementCapability())
        contract = ElementCapability.create_contract(suppress_common_words=True)
        result = run_capability("Fe in water", contract)

        assert result.status == Resolution.SUCCESS
        assert result.canonicalized_value == "Fe"
        assert result.span == (0, 2)
        assert result.suppressed_count >= 1
        assert (3, 5) in result.suppressed_spans
