"""Integration tests for the GTIN capability through the full pipeline.

Every attested spelling (compact, HRI-spaced, hyphen-grouped,
label-prefixed, AI-wrapped, quoted/bracketed, prose-carried) collapses to a
single 14-digit padded canonical; padded-vs-native mentions of the same
entity dedup, distinct entities fail fast. Prefix membership keys the
EAN-13 view (UPC-A ``614...`` -> ``061``) and skips the GTIN-14 packaging
indicator. ``native`` output renders the as-spelled length (presentation
seam only — provenance/status live at the canonical layer).
"""

from __future__ import annotations

import pytest

import paxman
from paxman.capabilities.GTIN.capability import GTINCapability
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


def _register_gtin() -> None:
    register_capability(GTINCapability())


PARSER_RULE = "Section 1-gtin-structure-check-digit"
LOOKUP_RULE = "Section 2-gs1-prefix"
VERIFIED_RULE = "Section 3-verified-liveness"

UPCA = "614141999996"
UPCA14 = "00614141999996"
EAN13 = "5012345670003"
EAN1314 = "05012345670003"
GTIN14 = "10614141999993"


class TestGTINPipelineSuccess:
    """All attested spellings collapse to one 14-digit padded canonical."""

    @pytest.mark.parametrize(
        ("text", "expected_value", "expected_span"),
        [
            # compact per length
            ("96385074", "00000096385074", (0, 8)),
            (UPCA, UPCA14, (0, 12)),
            (EAN13, EAN1314, (0, 13)),
            (GTIN14, GTIN14, (0, 14)),
            # padded-14 spelling is already canonical
            (UPCA14, UPCA14, (0, 14)),
            # HRI-spaced
            ("6 14141 99999 6", UPCA14, (0, 15)),
            ("1234 5670", "00000012345670", (0, 9)),
            # hyphen-grouped
            ("590-1234-12345-7", "05901234123457", (0, 16)),
            # label-prefixed
            (f"GTIN: {UPCA14}", UPCA14, (0, 20)),
            (f"upc-{UPCA}", UPCA14, (0, 16)),
            (f"EAN-13: {EAN13}", EAN1314, (0, 21)),
            (f"GTIN-14 {GTIN14}", GTIN14, (0, 22)),
            # AI-wrapped (AI 01 = GTIN)
            ("(01)03453120000011", "03453120000011", (0, 18)),
            ("(01) 03453120000011", "03453120000011", (0, 19)),
            ("AI 01 03453120000011", "03453120000011", (0, 20)),
            ("GTIN: (01)03453120000011", "03453120000011", (0, 24)),
            # quoted / bracketed
            (f'"{EAN13}"', EAN1314, (1, 14)),
            (f"[{EAN13}]", EAN1314, (1, 14)),
            # indicator-1 (GTIN-14) and indicator-2 (restricted circulation)
            ("2061414199993", "02061414199993", (0, 13)),
            # Bookland as a plain GTIN-13
            ("9780471117094", "09780471117094", (0, 13)),
        ],
    )
    def test_success_rows(
        self, text: str, expected_value: str, expected_span: tuple[int, int]
    ) -> None:
        _register_gtin()
        contract = GTINCapability.create_contract()
        result = paxman.canonicalize(text, contract)

        assert result.status == Resolution.SUCCESS
        assert result.canonicalized_value == expected_value
        assert len(result.canonicalized_value) == 14
        assert result.span == expected_span
        # Parser + prefix corroborate the same canonical (ADR-0012 case);
        # the verified rule is feature-gated off by default.
        assert {c.value for c in result.candidates} == {expected_value}
        assert {c.validation_rule for c in result.candidates} == {
            PARSER_RULE,
            LOOKUP_RULE,
        }
        for candidate in result.candidates:
            assert candidate.recognition_rule == "gtin_recognition"
            assert candidate.span == expected_span

    def test_padded_vs_native_dedup(self) -> None:
        # Two spellings of the SAME entity coalesce, not fail-fast.
        _register_gtin()
        contract = GTINCapability.create_contract()
        result = paxman.canonicalize(f"{UPCA14} and {UPCA}", contract)

        assert result.status == Resolution.SUCCESS
        assert result.canonicalized_value == UPCA14

    def test_provenance_authorities(self) -> None:
        _register_gtin()
        contract = GTINCapability.create_contract()
        result = paxman.canonicalize(EAN13, contract)

        assert result.status == Resolution.SUCCESS
        by_rule = {c.validation_rule: c for c in result.candidates}
        assert by_rule[PARSER_RULE].provenance[0].specification_name == (
            "GS1 General Specifications"
        )
        assert by_rule[LOOKUP_RULE].provenance[0].specification_name == (
            "GS1 Prefix allocation"
        )


class TestGTINPipelineInvalid:
    """Recognized shape, failed validation: no claim survives."""

    @pytest.mark.parametrize(
        "text",
        [
            "614141999997",  # bad check digit (parser rejects)
            "9991414199996",  # check-valid, unallocated 999 prefix (lookup rejects)
            "01234567",  # UPC-E collision shape: check digit 5 != 7 (parser rejects)
        ],
    )
    def test_invalid_rows(self, text: str) -> None:
        _register_gtin()
        contract = GTINCapability.create_contract()
        result = paxman.canonicalize(text, contract)

        assert result.status == Resolution.INVALID
        assert result.canonicalized_value is None
        assert len(result.candidates) == 0
        assert result.span is None

    def test_verified_pinned_only_miss_invalid(self) -> None:
        # Verified-gated miss: pin Section 3 as the only active validator
        # (include_verified keeps it past the feature filter). Against the
        # shipped-empty snapshot it rejects, nothing else can validate, so
        # recognized-but-unvalidated yields INVALID — the pinned-authority
        # mechanism of tests/integration/test_feature_gating.py.
        _register_gtin()
        contract = GTINCapability.create_contract(
            pinned_rules=(VERIFIED_RULE,), include_verified=True
        )
        result = paxman.canonicalize(EAN13, contract)

        assert result.status == Resolution.INVALID
        assert result.canonicalized_value is None
        assert len(result.candidates) == 0

    def test_verified_flag_extra_authority_non_veto(self) -> None:
        # With the default rule set, include_verified=True ADDS Section 3
        # alongside the always-active check-digit + prefix pair. Section 3
        # misses the shipped-empty snapshot and contributes no candidate,
        # but does not veto: parser+prefix corroborate the same value, so
        # the result stays SUCCESS. Same mechanism as the ISBN unallocated-
        # range row in tests/integration/test_pipeline.py (an extra active
        # authority's miss adds no provenance; it does not overturn the
        # surviving corroborated candidates).
        _register_gtin()
        contract = GTINCapability.create_contract(include_verified=True)
        result = paxman.canonicalize(EAN13, contract)

        assert result.status == Resolution.SUCCESS
        assert result.canonicalized_value == EAN1314
        assert {c.validation_rule for c in result.candidates} == {
            PARSER_RULE,
            LOOKUP_RULE,
        }


class TestGTINPipelineMissing:
    """No valid-shape run: prose, stems, UPC-E, glued label, full-width, bars."""

    @pytest.mark.parametrize(
        "text",
        [
            "hello world",
            "012345",  # UPC-E (6 digits) — deferred, never recognized
            "1234567",  # 7-digit stem
            "614141999",  # 9-digit stem
            "6141419999",  # 10-digit stem
            "61414199999",  # 11-digit stem
            "GTIN00614141999996",  # glued label
            "６１４１４１９９９９９６",  # fullwidth digit homoglyph
            "||| || |||| ||",  # bars-only (no digits at all)
        ],
    )
    def test_missing_rows(self, text: str) -> None:
        _register_gtin()
        contract = GTINCapability.create_contract()
        result = paxman.canonicalize(text, contract)

        assert result.status == Resolution.MISSING
        assert result.canonicalized_value is None
        assert len(result.candidates) == 0
        assert result.span is None


class TestGTINPipelineAmbiguity:
    """Two distinct entities fail fast; identical mentions coalesce."""

    def test_two_distinct_raise(self) -> None:
        _register_gtin()
        contract = GTINCapability.create_contract()
        with pytest.raises(MultipleMentionsError):
            paxman.canonicalize(f"{EAN13} {UPCA}", contract)

    def test_identical_coalesce_to_success(self) -> None:
        _register_gtin()
        contract = GTINCapability.create_contract()
        result = paxman.canonicalize(f"{UPCA} {UPCA}", contract)

        assert result.status == Resolution.SUCCESS
        assert result.canonicalized_value == UPCA14

    def test_native_output_same_entity_spellings_coalesce(self) -> None:
        # Regression: output_format is presentation only.
        # Two spellings of ONE entity must coalesce under "native" exactly
        # as under the default 14-digit format — identity decisions (the
        # single-value invariant, dedup, status) run on canonical values,
        # and format_value() applies only at result assembly.
        _register_gtin()
        contract = GTINCapability.create_contract(output_format="native")
        result = paxman.canonicalize(f"{UPCA14} and {UPCA}", contract)

        assert result.status == Resolution.SUCCESS
        assert result.canonicalized_value == UPCA14
        assert result.span == (0, 14)
        assert {c.value for c in result.candidates} == {UPCA14}

    def test_native_output_gtin8_vs_padded14_coalesce(self) -> None:
        # Same entity, lengths 8 and 14: the as-spelled first mention wins
        # the presentation of the coalesced canonical value.
        _register_gtin()
        contract = GTINCapability.create_contract(output_format="native")
        result = paxman.canonicalize("12345670 and 00000012345670", contract)

        assert result.status == Resolution.SUCCESS
        assert result.canonicalized_value == "12345670"
        assert result.span == (0, 8)

    def test_native_output_identical_spelling_coalesces(self) -> None:
        # Control: same-spelling mentions already coalesced under native
        # (both mentions render identically regardless of the format leak).
        _register_gtin()
        contract = GTINCapability.create_contract(output_format="native")
        result = paxman.canonicalize(f"{UPCA} {UPCA}", contract)

        assert result.status == Resolution.SUCCESS
        assert result.canonicalized_value == UPCA

    def test_native_output_distinct_entities_still_raise(self) -> None:
        # Control: presentation must not weaken the fail-fast invariant —
        # genuinely distinct canonical values still raise under "native".
        _register_gtin()
        contract = GTINCapability.create_contract(output_format="native")
        with pytest.raises(MultipleMentionsError):
            paxman.canonicalize(f"{EAN13} {UPCA}", contract)


class TestGTINPipelineContract:
    """Excluded/pinned filtering per the rule-publication map (ADR-0012)."""

    def test_excluded_lookup_vacuity_success(self) -> None:
        # No lookup authority in force: the check-valid parser candidate
        # stands via the vacuity exception, even for the 999 prefix.
        _register_gtin()
        contract = GTINCapability.create_contract(excluded_rules=[LOOKUP_RULE])
        result = paxman.canonicalize("9991414199996", contract)

        assert result.status == Resolution.SUCCESS
        assert result.canonicalized_value == "09991414199996"
        assert {c.validation_rule for c in result.candidates} == {PARSER_RULE}


class TestGTINPipelineIntegrity:
    """Span coverage, candidate dedup, determinism, and version stamping."""

    def test_span_includes_label_when_present(self) -> None:
        _register_gtin()
        contract = GTINCapability.create_contract()
        text = f"GTIN: {UPCA14}"
        result = paxman.canonicalize(text, contract)

        assert result.status == Resolution.SUCCESS
        assert result.span == (0, 20)
        assert text[result.span[0] : result.span[1]] == text

    def test_span_includes_ai_wrapper(self) -> None:
        _register_gtin()
        contract = GTINCapability.create_contract()
        text = "(01) 03453120000011"
        result = paxman.canonicalize(text, contract)

        assert result.status == Resolution.SUCCESS
        assert result.span == (0, 19)
        assert text[result.span[0] : result.span[1]] == text

    def test_span_prose_carrier_excludes_surroundings(self) -> None:
        _register_gtin()
        contract = GTINCapability.create_contract()
        text = "Batch 5012345670003 shipped."
        result = paxman.canonicalize(text, contract)

        assert result.status == Resolution.SUCCESS
        assert result.span == (6, 19)
        assert text[result.span[0] : result.span[1]] == EAN13

    def test_candidate_dedup_single_mention(self) -> None:
        _register_gtin()
        contract = GTINCapability.create_contract()
        result = paxman.canonicalize(UPCA, contract)

        assert result.status == Resolution.SUCCESS
        # one entity, one canonical value, two corroborating validations
        assert len(result.candidates) == 2
        assert {c.value for c in result.candidates} == {UPCA14}
        assert {c.span for c in result.candidates} == {(0, 12)}

    def test_determinism_spot_check(self) -> None:
        _register_gtin()
        contract = GTINCapability.create_contract()
        first = paxman.canonicalize(f"upc-{UPCA}", contract)
        second = paxman.canonicalize(f"upc-{UPCA}", contract)

        assert first.status == Resolution.SUCCESS
        assert first.canonicalized_value == second.canonicalized_value == UPCA14
        assert first.span == second.span == (0, 16)
        assert first.version_stamp == second.version_stamp

    def test_version_stamp_present(self) -> None:
        _register_gtin()
        contract = GTINCapability.create_contract()
        result = paxman.canonicalize(EAN13, contract)

        assert result.status == Resolution.SUCCESS
        assert result.version_stamp.paxman_version
        assert result.version_stamp.recognition_revision != "0"
