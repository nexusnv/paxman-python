"""Integration tests for the LEI capability through the full pipeline.

Compact/lowercase/single-spaced/``LEI:``-labelled/``urn:lei:``-carried
mentions coalesce to the compact uppercase canonical (ISO 17442-1:2020
structure + MOD 97-10 plus GLEIF accredited-LOU prefix membership);
the ``urn`` output format renders ``urn:lei:<compact>`` presentation-only.
"""

from __future__ import annotations

import pytest

import paxman
from paxman.capabilities.LEI.capability import LEICapability
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


def _register_lei() -> None:
    register_capability(LEICapability())


PARSER_RULE = "Section 4-lei-structure-mod97-10"
LOOKUP_RULE = "Section 1-lou-prefix-membership"

VALID = "213800KUD8LAJWSQ9D15"
OTHER = "5493000IBP32UQZ0KL24"
NON00 = "7LTWFZYICNSX8D621K86"


class TestLEIPipelineSuccess:
    """Bare, folded, spaced, labelled, and URN-carried forms collapse to compact."""

    @pytest.mark.parametrize(
        ("text", "expected_value", "expected_span"),
        [
            (VALID, VALID, (0, 20)),
            ("5493000ibp32uqz0kl24", OTHER, (0, 20)),
            ("5493 000IBP32UQZ0KL24", OTHER, (0, 21)),
            (f"LEI: {VALID}", VALID, (0, 25)),
            (f"lei {OTHER}", OTHER, (0, 24)),
            (f"LEI-{VALID}", VALID, (0, 24)),
            (f"urn:lei:{VALID}", VALID, (0, 28)),
            (f"URN:LEI:{OTHER}", OTHER, (0, 28)),
            (f"  {VALID}  ", VALID, (2, 22)),
            (f'"{VALID}"', VALID, (1, 21)),
            (f"[{OTHER}]", OTHER, (1, 21)),
            (NON00, NON00, (0, 20)),
            ("213800WSGIIZCXF1P572", "213800WSGIIZCXF1P572", (0, 20)),
            ("506700GE1G29325QX363", "506700GE1G29325QX363", (0, 20)),
            ("213800D1L3R2MWV39G88", "213800D1L3R2MWV39G88", (0, 20)),
        ],
    )
    def test_success_rows(
        self, text: str, expected_value: str, expected_span: tuple[int, int]
    ) -> None:
        _register_lei()
        contract = LEICapability.create_contract()
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
            assert candidate.recognition_rule == "lei_recognition"
            assert candidate.span == expected_span

    def test_provenance_authorities(self) -> None:
        _register_lei()
        contract = LEICapability.create_contract()
        result = paxman.canonicalize(VALID, contract)

        assert result.status == Resolution.SUCCESS
        by_rule = {c.validation_rule: c for c in result.candidates}
        assert by_rule[PARSER_RULE].provenance[0].specification_name == (
            "ISO 17442-1:2020"
        )
        assert by_rule[LOOKUP_RULE].provenance[0].specification_name == (
            "GLEIF LOU prefix list"
        )

    def test_urn_output_format(self) -> None:
        _register_lei()
        contract = LEICapability.create_contract(output_format="urn")
        result = paxman.canonicalize(OTHER, contract)

        assert result.status == Resolution.SUCCESS
        assert result.canonicalized_value == f"urn:lei:{OTHER}"
        assert {c.value for c in result.candidates} == {f"urn:lei:{OTHER}"}


class TestLEIPipelineInvalid:
    """Recognized shape, failed validation: no claim survives."""

    @pytest.mark.parametrize(
        "text",
        [
            "213800KUD8LXJWSQ9D15",  # bad check digit (parser rejects)
            "ZZZZ0000000000000016",  # checksum-valid, unknown prefix (lookup rejects)
        ],
    )
    def test_invalid_rows(self, text: str) -> None:
        _register_lei()
        contract = LEICapability.create_contract()
        result = paxman.canonicalize(text, contract)

        assert result.status == Resolution.INVALID
        assert result.canonicalized_value is None
        assert len(result.candidates) == 0
        assert result.span is None


class TestLEIPipelineMissing:
    """No valid-shape run: prose, hyphenated, glued, short/long, spaced, homoglyph."""

    @pytest.mark.parametrize(
        "text",
        [
            "hello world",
            "5493-000I-BP32-UQZ0-KL24",  # hyphenated (deferred to community grammars)
            "LEI5493000IBP32UQZ0KL24",  # glued label
            "213800KUD8LAJWSQ9D1",  # 19 chars
            "213800KUD8LAJWSQ9D155",  # 21 chars
            "5493  000IBP32UQZ0KL24",  # double space
            "5493\t000IBP32UQZ0KL24",  # tab
            "213800KUD8LAJWSQ9D1\uff15",  # fullwidth digit homoglyph
            "\uff15493000IBP32UQZ0KL24",  # fullwidth letter homoglyph
            "https://www.gleif.org/lei-data213800KUD8LAJWSQ9D15",  # glued URL
        ],
    )
    def test_missing_rows(self, text: str) -> None:
        _register_lei()
        contract = LEICapability.create_contract()
        result = paxman.canonicalize(text, contract)

        assert result.status == Resolution.MISSING
        assert result.canonicalized_value is None
        assert len(result.candidates) == 0
        assert result.span is None


class TestLEIPipelineAmbiguity:
    """Two distinct LEIs fail fast; identical mentions coalesce."""

    def test_two_distinct_raise(self) -> None:
        _register_lei()
        contract = LEICapability.create_contract()
        with pytest.raises(MultipleMentionsError):
            paxman.canonicalize(f"{VALID} {OTHER}", contract)

    def test_identical_coalesce_to_success(self) -> None:
        _register_lei()
        contract = LEICapability.create_contract()
        result = paxman.canonicalize(f"{VALID} {VALID}", contract)

        assert result.status == Resolution.SUCCESS
        assert result.canonicalized_value == VALID


class TestLEIPipelineContract:
    """Excluded/pinned/year filtering per the rule-publication map."""

    def test_excluded_lou_rule_false_success(self) -> None:
        # Excluding the LOOKUP_TABLE prefix rule leaves the checksum-only
        # PARSER active; with no lookup authority in force the vacuity
        # exception (ADR-0012) lets the parser candidate stand → SUCCESS.
        _register_lei()
        contract = LEICapability.create_contract(excluded_rules=[LOOKUP_RULE])
        result = paxman.canonicalize(VALID, contract)

        assert result.status == Resolution.SUCCESS
        assert result.canonicalized_value == VALID
        assert {c.validation_rule for c in result.candidates} == {PARSER_RULE}

    def test_pinned_year_filter(self) -> None:
        # Pinning to the parser alone also succeeds (same vacuity path).
        _register_lei()
        contract = LEICapability.create_contract(pinned_rules=[PARSER_RULE])
        result = paxman.canonicalize(VALID, contract)

        assert result.status == Resolution.SUCCESS
        assert result.canonicalized_value == VALID

        # year=2026 keeps both publications (2020 + Rolling/2026) → SUCCESS.
        reset_registry()
        _register_lei()
        contract_2026 = LEICapability.create_contract(year=2026)
        result_2026 = paxman.canonicalize(VALID, contract_2026)

        assert result_2026.status == Resolution.SUCCESS
        assert result_2026.canonicalized_value == VALID

        # year=2020 drops the 2026 lookup rule → parser-only SUCCESS.
        reset_registry()
        _register_lei()
        contract_2020 = LEICapability.create_contract(year=2020)
        result_2020 = paxman.canonicalize(VALID, contract_2020)

        assert result_2020.status == Resolution.SUCCESS
        assert {c.validation_rule for c in result_2020.candidates} == {PARSER_RULE}

        # year=2019 drops both rules → recognized but unvalidated → INVALID.
        reset_registry()
        _register_lei()
        contract_2019 = LEICapability.create_contract(year=2019)
        result_2019 = paxman.canonicalize(VALID, contract_2019)

        assert result_2019.status == Resolution.INVALID
        assert result_2019.canonicalized_value is None
        assert len(result_2019.candidates) == 0


class TestLEIPipelineIntegrity:
    """Span coverage, determinism, and version stamping."""

    def test_span_includes_label_when_present(self) -> None:
        _register_lei()
        contract = LEICapability.create_contract()
        text = f"LEI: {VALID}"
        result = paxman.canonicalize(text, contract)

        assert result.status == Resolution.SUCCESS
        assert result.span == (0, 25)
        assert text[result.span[0] : result.span[1]] == text

    def test_span_excludes_outer_whitespace(self) -> None:
        _register_lei()
        contract = LEICapability.create_contract()
        text = f"  {VALID}  "
        result = paxman.canonicalize(text, contract)

        assert result.status == Resolution.SUCCESS
        assert result.span == (2, 22)
        assert text[result.span[0] : result.span[1]] == VALID

    def test_determinism_spot_check(self) -> None:
        _register_lei()
        contract = LEICapability.create_contract()
        first = paxman.canonicalize(f"LEI: {OTHER.lower()}", contract)
        second = paxman.canonicalize(f"LEI: {OTHER.lower()}", contract)

        assert first.status == Resolution.SUCCESS
        assert first.canonicalized_value == second.canonicalized_value == OTHER
        assert first.span == second.span == (0, 25)
        assert first.version_stamp == second.version_stamp

    def test_version_stamp_present(self) -> None:
        _register_lei()
        contract = LEICapability.create_contract()
        result = paxman.canonicalize(VALID, contract)

        assert result.status == Resolution.SUCCESS
        assert result.version_stamp.paxman_version
        assert result.version_stamp.recognition_revision != "0"
