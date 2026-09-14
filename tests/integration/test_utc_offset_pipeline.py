"""Integration tests for the UtcOffset capability through the full pipeline.

Research acceptance corpus: ``docs/development/research/2026-09-14-timezone-
canonicalization.md`` §8 edge table (offset rows 5-8, 17) + §7.4 offset
semantics + post-review semantic matrix (offset rows). Every vector below
was executed against the pipeline (``register_all_shipped`` +
``canonicalize``); statuses are observed, not assumed. One deliberate
divergence from the research table is pinned with rationale:

- out-of-range *prefixed* offsets (``UTC+15:00``): research §8 row 17
  assumes rule-level refusal (INVALID), but the shipped grammar carries
  the ``|HH| ≤ 14`` range guard itself (research §4.4 guard table), so
  the shape is never claimed and the outcome is MISSING. Bare
  out-of-range shapes the grammar does claim (``+14:30``) are INVALID
  via the rule's signed total-minutes bound — both outcomes pinned below.
"""

from __future__ import annotations

from collections.abc import Iterator

import pytest

import paxman
from paxman.capabilities.UtcOffset.capability import UtcOffsetCapability
from paxman.core.discovery import reset_registry
from paxman.core.domain import Resolution
from paxman.core.errors import ContractError, MultipleMentionsError

_STRUCTURE_RULE = "Section offset-structure"


@pytest.fixture(autouse=True)
def _clean_registry() -> Iterator[None]:
    """Reset the capability registry before and after each test."""
    reset_registry()
    yield
    reset_registry()


class TestUtcOffsetPipelineSuccess:
    """§8 rows 6-7 + §7.4 human-notation semantics + matrix offset rows."""

    @pytest.mark.integration
    @pytest.mark.parametrize(
        ("text", "expected_value", "expected_span"),
        [
            ("UTC+5", "+05:00", (0, 5)),
            ("utc+5", "+05:00", (0, 5)),
            ("GMT+5", "+05:00", (0, 5)),
            ("GMT-05:30", "-05:30", (0, 9)),
            ("UTC+05:30", "+05:30", (0, 9)),
            ("+0530", "+05:30", (0, 5)),
            ("+05", "+05:00", (0, 3)),
            ("+05:30", "+05:30", (0, 6)),
            ("-08:00", "-08:00", (0, 6)),
            ("Z", "+00:00", (0, 1)),
            ("z", "+00:00", (0, 1)),
            ("+14:00", "+14:00", (0, 6)),
            ("-12:00", "-12:00", (0, 6)),
        ],
    )
    def test_success_rows(
        self, text: str, expected_value: str, expected_span: tuple[int, int]
    ) -> None:
        """Human-notation offsets normalize to canonical +HH:MM."""
        paxman.register_all_shipped()
        contract = UtcOffsetCapability.create_contract()
        result = paxman.canonicalize(text, contract)

        assert result.status == Resolution.SUCCESS
        assert result.canonicalized_value == expected_value
        assert result.span == expected_span
        assert len(result.candidates) >= 1
        assert {c.value for c in result.candidates} == {expected_value}
        for candidate in result.candidates:
            assert candidate.validation_rule == _STRUCTURE_RULE
            assert candidate.provenance[0].authority == "ISO"

    @pytest.mark.integration
    def test_embedded_offset_span(self) -> None:
        """Offsets are recognized inside prose with exact spans."""
        paxman.register_all_shipped()
        contract = UtcOffsetCapability.create_contract()
        result = paxman.canonicalize("meeting at +05:30 tomorrow", contract)

        assert result.status == Resolution.SUCCESS
        assert result.canonicalized_value == "+05:30"
        assert result.span == (11, 17)

    @pytest.mark.integration
    def test_basic_output_format_roundtrip(self) -> None:
        """The offered basic re-encoding renders and re-enters (ADR-0010)."""
        paxman.register_all_shipped()
        contract = UtcOffsetCapability.create_contract(output_format="basic")
        result = paxman.canonicalize("+0530", contract)

        assert result.status == Resolution.SUCCESS
        assert result.canonicalized_value == "+0530"
        again = paxman.canonicalize("+0530", contract)
        assert again.status == Resolution.SUCCESS
        assert again.canonicalized_value == "+0530"


class TestUtcOffsetPipelineRefusal:
    """§8 rows 8, 17 (bare-shape half) + matrix unknown-offset row."""

    @pytest.mark.integration
    def test_unknown_offset_invalid(self) -> None:
        """§8 row 8: -00:00 states ignorance of the offset, a different
        entity from zero — refused, never normalized."""
        paxman.register_all_shipped()
        contract = UtcOffsetCapability.create_contract()
        result = paxman.canonicalize("-00:00", contract)

        assert result.status == Resolution.INVALID
        assert result.canonicalized_value is None
        assert result.candidates == ()

    @pytest.mark.integration
    @pytest.mark.parametrize("text", ["+14:30", "-12:30"])
    def test_beyond_real_world_range_invalid(self, text: str) -> None:
        """Claimed bare shapes past the signed total-minutes bound fail
        in the rule (Kiritimati +14:00 / Baker Island -12:00 hold)."""
        paxman.register_all_shipped()
        contract = UtcOffsetCapability.create_contract()
        result = paxman.canonicalize(text, contract)

        assert result.status == Resolution.INVALID
        assert result.canonicalized_value is None
        assert result.candidates == ()


class TestUtcOffsetPipelineMissing:
    """§8 row 5 (guard half) + §8 row 17 (prefixed half) + §8 row 18."""

    @pytest.mark.integration
    def test_prefixed_beyond_maximum_missing(self) -> None:
        """§8 row 17 executed: UTC+15:00 is never claimed (grammar range
        guard per §4.4), hence MISSING (see module docstring)."""
        paxman.register_all_shipped()
        contract = UtcOffsetCapability.create_contract()
        result = paxman.canonicalize("UTC+15:00", contract)

        assert result.status == Resolution.MISSING
        assert result.canonicalized_value is None
        assert result.candidates == ()

    @pytest.mark.integration
    def test_etc_key_yields_no_offset(self) -> None:
        """§8 row 5: slash-aware lookbehind — no mid-key extraction from
        Etc/GMT+5; the key belongs solely to Timezone."""
        paxman.register_all_shipped()
        contract = UtcOffsetCapability.create_contract()
        result = paxman.canonicalize("Etc/GMT+5", contract)

        assert result.status == Resolution.MISSING
        assert result.canonicalized_value is None
        assert result.candidates == ()

    @pytest.mark.integration
    def test_zulu_word_missing(self) -> None:
        """§8 row 18: Zulu is military prose, not the Z designator."""
        paxman.register_all_shipped()
        contract = UtcOffsetCapability.create_contract()
        result = paxman.canonicalize("Zulu", contract)

        assert result.status == Resolution.MISSING
        assert result.canonicalized_value is None
        assert result.candidates == ()

    @pytest.mark.integration
    @pytest.mark.parametrize(
        "text",
        ["+05:60", "+05:6", "+5:60", "UTC+5:60", "+05:00:00", "++05:00", "--05:00"],
    )
    def test_truncated_or_garbage_offsets_missing(self, text: str) -> None:
        """Partial-minute fragments and sign garbage must not emit a
        truncated prefix (#162 — truncated SUCCESS is a wrong value)."""
        paxman.register_all_shipped()
        contract = UtcOffsetCapability.create_contract()
        result = paxman.canonicalize(text, contract)

        assert result.status == Resolution.MISSING
        assert result.canonicalized_value is None
        assert result.candidates == ()


class TestUtcOffsetPipelineContract:
    """Ambiguity + unoffered formats + determinism."""

    @pytest.mark.integration
    def test_two_distinct_offsets_raise(self) -> None:
        """Two distinct offsets fail fast (single_value=True)."""
        paxman.register_all_shipped()
        contract = UtcOffsetCapability.create_contract()
        with pytest.raises(MultipleMentionsError):
            paxman.canonicalize("+05:30 and -08:00", contract)

    @pytest.mark.integration
    def test_unoffered_format_contract_error(self) -> None:
        """Only basic is offered (presentation-only re-encoding); anything
        else raises ContractError at contract construction."""
        paxman.register_all_shipped()
        with pytest.raises(ContractError):
            UtcOffsetCapability.create_contract(output_format="abbreviation")

    @pytest.mark.integration
    def test_determinism_spot_check(self) -> None:
        """Same input + contract + snapshot → same output (no clock)."""
        paxman.register_all_shipped()
        contract = UtcOffsetCapability.create_contract()
        first = paxman.canonicalize("UTC+5", contract)
        second = paxman.canonicalize("UTC+5", contract)

        assert first.status == Resolution.SUCCESS
        assert (second.status, second.canonicalized_value, second.span) == (
            first.status,
            first.canonicalized_value,
            first.span,
        )
