"""Integration tests for the ISIN capability through the full pipeline.

Research vectors: ISO 6166:2021 (structure + mod-10 check digit) and the
ANNA ISIN Guidelines V25 (country/special prefix allowlist); audited
2026-09-20 per docs/development/plans/2026-09-21-isin-capability.md §2.
All §2 surface variants coalesce to the compact uppercase canonical; the
``grouped`` output format renders ``CC NNNNNN NNN C`` presentation-only.
"""

from __future__ import annotations

import pytest

import paxman
from paxman.capabilities.ISIN.capability import ISINCapability
from paxman.core.discovery import register_capability, reset_registry
from paxman.core.domain import Resolution
from paxman.core.errors import MultipleMentionsError

pytestmark = [pytest.mark.integration]


@pytest.fixture(autouse=True)
def _clean_registry():
    """Reset the capability registry before and after each test."""
    reset_registry()
    yield
    reset_registry()


def _register_isin() -> None:
    register_capability(ISINCapability())


PARSER_RULE = "Section 4-isin-structure-check-digit"
LOOKUP_RULE = "Section 5-country-and-special-prefix"


class TestISINPipelineSuccess:
    """Bare, folded, spaced, and labelled carriers collapse to compact."""

    @pytest.mark.parametrize(
        ("text", "expected_value", "expected_span"),
        [
            ("US0378331005", "US0378331005", (0, 12)),
            ("us0378331005", "US0378331005", (0, 12)),
            ("US 037833 100 5", "US0378331005", (0, 15)),
            ("ISIN: US0378331005", "US0378331005", (0, 18)),
            ("  US0378331005  ", "US0378331005", (2, 14)),
            ("AU0000XVGZA3", "AU0000XVGZA3", (0, 12)),
            ("GB0002634946", "GB0002634946", (0, 12)),
            ("XS0931417173", "XS0931417173", (0, 12)),
            ("XTV15WLZJMF0", "XTV15WLZJMF0", (0, 12)),
            ("FR0000120271", "FR0000120271", (0, 12)),
            ("PL0000503132", "PL0000503132", (0, 12)),
            ("PLPKN0000018", "PLPKN0000018", (0, 12)),
            ("IS0000000008", "IS0000000008", (0, 12)),
        ],
    )
    def test_success_rows(
        self, text: str, expected_value: str, expected_span: tuple[int, int]
    ) -> None:
        _register_isin()
        contract = ISINCapability.create_contract()
        result = paxman.canonicalize(text, contract)

        assert result.status == Resolution.SUCCESS
        assert result.canonicalized_value == expected_value
        assert result.span == expected_span
        # Both rules agree on the compact value (ADR-0012 corroborated case).
        assert {c.value for c in result.candidates} == {expected_value}
        assert {c.validation_rule for c in result.candidates} == {
            PARSER_RULE,
            LOOKUP_RULE,
        }
        for candidate in result.candidates:
            assert candidate.recognition_rule == "isin_recognition"
            assert candidate.span == expected_span

    def test_provenance_authorities(self) -> None:
        _register_isin()
        contract = ISINCapability.create_contract()
        result = paxman.canonicalize("US0378331005", contract)

        assert result.status == Resolution.SUCCESS
        by_rule = {c.validation_rule: c for c in result.candidates}
        assert by_rule[PARSER_RULE].provenance[0].specification_name == "ISO 6166:2021"
        assert (
            by_rule[LOOKUP_RULE].provenance[0].specification_name
            == "ANNA ISIN Guidelines"
        )

    def test_grouped_output_format(self) -> None:
        _register_isin()
        contract = ISINCapability.create_contract(output_format="grouped")
        result = paxman.canonicalize("US0378331005", contract)

        assert result.status == Resolution.SUCCESS
        assert result.canonicalized_value == "US 037833 100 5"
        assert {c.value for c in result.candidates} == {"US 037833 100 5"}


class TestISINPipelineInvalid:
    """Recognized shape, failed validation: no claim survives."""

    @pytest.mark.parametrize(
        "text",
        [
            "US0378331003",  # bad check digit (parser rejects)
            "XX0378331005",  # checksum-valid, unknown prefix (lookup rejects)
            "ZZ0378331001",  # checksum-valid, provisional prefix (lookup rejects)
        ],
    )
    def test_invalid_rows(self, text: str) -> None:
        _register_isin()
        contract = ISINCapability.create_contract()
        result = paxman.canonicalize(text, contract)

        assert result.status == Resolution.INVALID
        assert result.canonicalized_value is None
        assert len(result.candidates) == 0
        assert result.span is None


class TestISINPipelineMissing:
    """No valid-shape run: hyphenated, glued, short/long, letter, homoglyph."""

    @pytest.mark.parametrize(
        "text",
        [
            "hello world",
            "US-037833100-5",
            "ISINUS0378331005",
            "US037833100",
            "US03783310055",
            "US037833100A",
            "\uff35\uff330378331005",
        ],
    )
    def test_missing_rows(self, text: str) -> None:
        _register_isin()
        contract = ISINCapability.create_contract()
        result = paxman.canonicalize(text, contract)

        assert result.status == Resolution.MISSING
        assert result.canonicalized_value is None
        assert len(result.candidates) == 0
        assert result.span is None


class TestISINPipelineAmbiguity:
    """Two distinct ISINs fail fast; identical mentions coalesce."""

    def test_two_distinct_raise(self) -> None:
        _register_isin()
        contract = ISINCapability.create_contract()
        with pytest.raises(MultipleMentionsError):
            paxman.canonicalize("US0378331005 GB0002634946", contract)

    def test_identical_coalesce_to_success(self) -> None:
        _register_isin()
        contract = ISINCapability.create_contract()
        result = paxman.canonicalize("US0378331005 US0378331005", contract)

        assert result.status == Resolution.SUCCESS
        assert result.canonicalized_value == "US0378331005"


class TestISINPipelineContract:
    """Excluded/pinned/year filtering per the rule-publication map."""

    def test_excluded_prefix_rule_false_success(self) -> None:
        # Excluding the LOOKUP_TABLE prefix rule leaves the checksum-only
        # PARSER active; with no lookup authority in force the vacuity
        # exception (ADR-0012) lets the parser candidate stand → SUCCESS.
        _register_isin()
        contract = ISINCapability.create_contract(excluded_rules=[LOOKUP_RULE])
        result = paxman.canonicalize("US0378331005", contract)

        assert result.status == Resolution.SUCCESS
        assert result.canonicalized_value == "US0378331005"
        assert {c.validation_rule for c in result.candidates} == {PARSER_RULE}

    def test_pinned_year_filter(self) -> None:
        # Pinning to the parser alone also succeeds (same vacuity path).
        _register_isin()
        contract = ISINCapability.create_contract(pinned_rules=[PARSER_RULE])
        result = paxman.canonicalize("US0378331005", contract)

        assert result.status == Resolution.SUCCESS
        assert result.canonicalized_value == "US0378331005"

        # year=2025 keeps both publications (2021 + 2025) → SUCCESS.
        reset_registry()
        _register_isin()
        contract_2025 = ISINCapability.create_contract(year=2025)
        result_2025 = paxman.canonicalize("US0378331005", contract_2025)

        assert result_2025.status == Resolution.SUCCESS
        assert result_2025.canonicalized_value == "US0378331005"

        # year=2021 drops the 2025 lookup rule → parser-only SUCCESS.
        reset_registry()
        _register_isin()
        contract_2021 = ISINCapability.create_contract(year=2021)
        result_2021 = paxman.canonicalize("US0378331005", contract_2021)

        assert result_2021.status == Resolution.SUCCESS
        assert {c.validation_rule for c in result_2021.candidates} == {PARSER_RULE}

        # year=2020 drops both rules → recognized but unvalidated → INVALID.
        reset_registry()
        _register_isin()
        contract_2020 = ISINCapability.create_contract(year=2020)
        result_2020 = paxman.canonicalize("US0378331005", contract_2020)

        assert result_2020.status == Resolution.INVALID
        assert result_2020.canonicalized_value is None
        assert len(result_2020.candidates) == 0


class TestISINPipelineIntegrity:
    """Span coverage, determinism, and version stamping."""

    def test_span_includes_label_when_present(self) -> None:
        _register_isin()
        contract = ISINCapability.create_contract()
        text = "ISIN: US0378331005"
        result = paxman.canonicalize(text, contract)

        assert result.status == Resolution.SUCCESS
        assert result.span == (0, 18)
        assert text[result.span[0] : result.span[1]] == text

    def test_span_excludes_outer_whitespace(self) -> None:
        _register_isin()
        contract = ISINCapability.create_contract()
        text = "  US0378331005  "
        result = paxman.canonicalize(text, contract)

        assert result.status == Resolution.SUCCESS
        assert result.span == (2, 14)
        assert text[result.span[0] : result.span[1]] == "US0378331005"

    def test_determinism_spot_check(self) -> None:
        _register_isin()
        contract = ISINCapability.create_contract()
        first = paxman.canonicalize("ISIN: us0378331005", contract)
        second = paxman.canonicalize("ISIN: us0378331005", contract)

        assert first.status == Resolution.SUCCESS
        assert first.canonicalized_value == second.canonicalized_value == "US0378331005"
        assert first.span == second.span == (0, 18)
        assert first.version_stamp == second.version_stamp

    def test_version_stamp_present(self) -> None:
        _register_isin()
        contract = ISINCapability.create_contract()
        result = paxman.canonicalize("US0378331005", contract)

        assert result.status == Resolution.SUCCESS
        assert result.version_stamp.paxman_version
        assert result.version_stamp.recognition_revision != "0"
