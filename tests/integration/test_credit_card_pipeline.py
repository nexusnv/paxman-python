"""Integration tests for the CreditCard capability through the full pipeline.

Compact/spaced/dashed/Amex-4-6-5/Diners-14/mixed-separator/labelled PAN
mentions coalesce to the compact contiguous-digit canonical (ISO/IEC
7812-1:2017 structure + Luhn MOD-10 Annex B); the ``grouped`` output format
renders a groups-of-4 re-chunk presentation-only (Amex 15 renders 4-4-4-3,
never brand 4-6-5); the gated brand-prefix rule duplicates Luhn as ADR-0012
corroboration, never a waiver.
"""

from __future__ import annotations

import pytest

import paxman
from paxman.capabilities.CreditCard.capability import CreditCardCapability
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


def _register_credit_card() -> None:
    register_capability(CreditCardCapability())


ISO_RULE = "Section 5-pan-structure-luhn"
BRAND_RULE = "Section 1-brand-prefix-membership"
REC_RULE = "pan_recognition"
VISA = "4111111111111111"


class TestCreditCardPipelineSuccess:
    """Every §2.1 RECOGNIZE written form collapses to the compact canonical."""

    @pytest.mark.parametrize(
        ("text", "expected_value", "expected_span"),
        [
            # the seven RECOGNIZE rows: compact / spaced / dashed / Amex
            # 4-6-5 / Diners-14 / mixed space-hyphen / label-prefixed prose
            (VISA, VISA, (0, 16)),
            ("4111 1111 1111 1111", VISA, (0, 19)),
            ("4716-2210-5188-5662", "4716221051885662", (0, 19)),
            ("3782 822463 10005", "378282246310005", (0, 17)),
            ("3622 720627 1667", "36227206271667", (0, 16)),
            ("4111 1111-1111 1111", VISA, (0, 19)),
            ("PAN: 4111 1111 1111 1111", VISA, (0, 24)),  # label-inclusive span
        ],
    )
    def test_success_all_recognize_forms(
        self, text: str, expected_value: str, expected_span: tuple[int, int]
    ) -> None:
        _register_credit_card()
        contract = CreditCardCapability.create_contract()
        result = paxman.canonicalize(text, contract)

        assert result.status == Resolution.SUCCESS
        assert result.canonicalized_value == expected_value
        assert result.span == expected_span
        for candidate in result.candidates:
            assert candidate.span == expected_span

    def test_success_twins_coalesce(self) -> None:
        # Spaced + compact + dashed twins of one PAN → one canonical
        # (identical-value mentions coalesce, never MultipleMentionsError).
        _register_credit_card()
        contract = CreditCardCapability.create_contract()
        text = "4111 1111 1111 1111, 4111111111111111, 4111-1111-1111-1111"
        result = paxman.canonicalize(text, contract)

        assert result.status == Resolution.SUCCESS
        assert result.canonicalized_value == VISA

    def test_expiry_span_success(self) -> None:
        # Expiry-glued multi-field string: recognize the PAN span only.
        _register_credit_card()
        contract = CreditCardCapability.create_contract()
        result = paxman.canonicalize("4111111111111111 12/27", contract)

        assert result.status == Resolution.SUCCESS
        assert result.canonicalized_value == VISA
        assert result.span == (0, 16)


class TestCreditCardPipelineInvalid:
    """Recognized shape, failed validation: no claim survives."""

    @pytest.mark.parametrize(
        "text",
        [
            "4111111111111112",  # last digit flipped (Luhn fails)
            "5398228707871528",  # validator.js invalid fixture
            "41111111111111111",  # 17-run claimed whole, never a 16-carve
            "order 12 4111111111111111",  # soft-joined prose → 18-run claim
        ],
    )
    def test_invalid_luhn_and_whole_run_claims(self, text: str) -> None:
        _register_credit_card()
        contract = CreditCardCapability.create_contract()
        result = paxman.canonicalize(text, contract)

        assert result.status == Resolution.INVALID
        assert result.canonicalized_value is None
        assert len(result.candidates) == 0
        assert result.span is None


class TestCreditCardPipelineMissing:
    """No claimable PAN run: short/masked/truncated/letter-glued/20-digit/
    double-space/tab/under-floor."""

    @pytest.mark.parametrize(
        "text",
        [
            "41111111111",  # 11-digit short (below the 12 floor)
            "41111111",  # under-8
            "4111-XXXX-XXXX-1111",  # masked display (handling output)
            "XXXX XXXX XXXX 1234",  # masked display (handling output)
            "411111...1111",  # truncated first-6/last-4 storage display
            "X4111111111111111",  # letter glued left
            "4111111111111111Y",  # letter glued right
            "A4111111111111111B",  # letter glued both sides
            "41111111111111111111",  # compact 20-digit run (over ceiling)
            "4111 1111 1111 1111 1111",  # spaced 20-digit run
            "41111111111111111227",  # expiry-fused 20-digit run (no 16-carve)
            "4111  1111 1111 1111",  # double space: documented non-recognition
            "4111\t1111\t1111\t1111",  # tab: documented non-recognition
        ],
    )
    def test_missing_non_pan_surfaces(self, text: str) -> None:
        _register_credit_card()
        contract = CreditCardCapability.create_contract()
        result = paxman.canonicalize(text, contract)

        assert result.status == Resolution.MISSING
        assert result.canonicalized_value is None
        assert len(result.candidates) == 0
        assert result.span is None


class TestCreditCardPipelineAmbiguity:
    """Two distinct PANs fail fast; identical mentions coalesce."""

    @pytest.mark.parametrize(
        "text",
        [
            f"{VISA} 5555555555554444",  # space-adjacent distinct pair
            f"{VISA}-5555555555554444",  # hyphen-adjacent distinct pair
        ],
    )
    def test_two_distinct_mentions_error(self, text: str) -> None:
        _register_credit_card()
        contract = CreditCardCapability.create_contract()
        with pytest.raises(MultipleMentionsError):
            paxman.canonicalize(text, contract)


class TestCreditCardBrandGate:
    """Brand rule gated off by default; opted in it never waives Luhn."""

    def test_brand_default_off_generic_success(self) -> None:
        # Luhn-valid but unknown prefix: generic-valid with the gate off.
        _register_credit_card()
        contract = CreditCardCapability.create_contract()
        result = paxman.canonicalize("9999999999999995", contract)

        assert result.status == Resolution.SUCCESS
        assert result.canonicalized_value == "9999999999999995"
        assert {c.validation_rule for c in result.candidates} == {ISO_RULE}

    def test_brand_opted_in_brand_invalid(self) -> None:
        # Same input with the gate on: no allowlisted brand → INVALID
        # (ADR-0012: the ISO PARSER needs LOOKUP corroboration).
        _register_credit_card()
        contract = CreditCardCapability.create_contract(include_brand_validation=True)
        result = paxman.canonicalize("9999999999999995", contract)

        assert result.status == Resolution.INVALID
        assert result.canonicalized_value is None
        assert len(result.candidates) == 0

    @pytest.mark.parametrize("gate", [False, True])
    def test_unionpay_invalid_under_every_contract(self, gate: bool) -> None:
        # Luhn-invalid 62-prefix: INVALID with the gate off (ISO rule) and
        # on (both rules) — the brand rule duplicates Luhn, never waives it.
        _register_credit_card()
        contract = CreditCardCapability.create_contract(include_brand_validation=gate)
        result = paxman.canonicalize("6200000000000001", contract)

        assert result.status == Resolution.INVALID
        assert result.canonicalized_value is None
        assert len(result.candidates) == 0


class TestCreditCardContract:
    """Excluded-rule vacuity, determinism, and span-bearing provenance."""

    def test_excluded_iso_rule_brand_vacuity(self) -> None:
        # Excluding the ISO PARSER leaves only the gated brand LOOKUP active;
        # with no PARSER authority in force the candidate stands → SUCCESS.
        _register_credit_card()
        contract = CreditCardCapability.create_contract(
            excluded_rules=[ISO_RULE], include_brand_validation=True
        )
        result = paxman.canonicalize(VISA, contract)

        assert result.status == Resolution.SUCCESS
        assert result.canonicalized_value == VISA
        assert {c.validation_rule for c in result.candidates} == {BRAND_RULE}

    def test_determinism_and_versionstamp(self) -> None:
        _register_credit_card()
        text = "PAN: 4111 1111 1111 1111"
        first = paxman.canonicalize(text, CreditCardCapability.create_contract())
        second = paxman.canonicalize(text, CreditCardCapability.create_contract())

        assert first.status == second.status == Resolution.SUCCESS
        assert first.canonicalized_value == second.canonicalized_value
        assert first.span == second.span
        assert first.version_stamp == second.version_stamp
        assert isinstance(first.version_stamp.paxman_version, str)

    def test_span_bearing_provenance(self) -> None:
        # Candidates carry span + recognition/validation rule names; the
        # ISO authority fronts the provenance. Grouped and compact
        # renderings share provenance (format_value is presentation-only).
        _register_credit_card()
        text = "4111 1111 1111 1111"
        result = paxman.canonicalize(text, CreditCardCapability.create_contract())

        assert result.status == Resolution.SUCCESS
        assert result.span == (0, 19)
        assert len(result.candidates) > 0
        for candidate in result.candidates:
            assert candidate.recognition_rule == REC_RULE
            assert candidate.validation_rule == ISO_RULE
            assert candidate.span == result.span
            assert text[candidate.span[0] : candidate.span[1]] == text
            assert candidate.provenance[0].authority == "ISO/IEC"
            assert candidate.provenance[0].specification_name == "ISO/IEC 7812-1:2017"

        grouped = paxman.canonicalize(
            text, CreditCardCapability.create_contract(output_format="grouped")
        )
        compact = paxman.canonicalize(
            text, CreditCardCapability.create_contract(output_format="pan")
        )

        assert grouped.canonicalized_value == text  # 4-4-4-4 re-chunk
        assert compact.canonicalized_value == VISA
        assert [tuple(c.provenance) for c in grouped.candidates] == [
            tuple(c.provenance) for c in compact.candidates
        ]
