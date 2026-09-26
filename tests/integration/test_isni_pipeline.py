"""Integration tests for the ISNI capability through the full pipeline.

Resolution-state map: research `2026-09-26-isni-canonicalization.md` §9.
Every vector below was executed against the pipeline
(`register_all_shipped` + `canonicalize`); statuses are observed, not assumed.
"""

from __future__ import annotations

from collections.abc import Iterator

import pytest

import paxman
from paxman.capabilities.ISNI.capability import ISNICapability
from paxman.core.discovery import reset_registry
from paxman.core.domain import Resolution
from paxman.core.errors import ContractError, MultipleMentionsError

_STRUCTURE_RULE = "Section 4-isni-structure"
_CHECK_RULE = "Section A-mod11-2-check-character"


@pytest.fixture(autouse=True)
def _clean_registry() -> Iterator[None]:
    """Reset the capability registry before and after each test."""
    reset_registry()
    yield
    reset_registry()


class TestISNIPipelineSuccess:
    """§9 SUCCESS rows: every spelling resolves to the spaced canonical."""

    @pytest.mark.parametrize(
        ("text", "expected", "span"),
        [
            ("ISNI 0000 0001 2103 2683", "0000 0001 2103 2683", (0, 24)),
            ("0000 0001 2103 2683", "0000 0001 2103 2683", (0, 19)),
            ("0000000121032683", "0000 0001 2103 2683", (0, 16)),
            ("0000-0001-2103-2683", "0000 0001 2103 2683", (0, 19)),
            (
                "https://isni.org/isni/0000000121032683",
                "0000 0001 2103 2683",
                (0, 38),
            ),
            ("urn:isni:0000000121032683", "0000 0001 2103 2683", (0, 25)),
            ("0000 0001 2281 955x", "0000 0001 2281 955X", (0, 19)),
        ],
    )
    def test_success_rows(
        self, text: str, expected: str, span: tuple[int, int]
    ) -> None:
        paxman.register_all_shipped()
        contract = ISNICapability.create_contract()
        result = paxman.canonicalize(text, contract)

        assert result.status == Resolution.SUCCESS
        assert result.canonicalized_value == expected
        assert result.span == span
        assert {c.validation_rule for c in result.candidates} == {
            _STRUCTURE_RULE,
            _CHECK_RULE,
        }

    def test_output_format_compact(self) -> None:
        paxman.register_all_shipped()
        contract = ISNICapability.create_contract(output_format="compact")
        result = paxman.canonicalize("ISNI 0000 0001 2103 2683", contract)

        assert result.status == Resolution.SUCCESS
        assert result.canonicalized_value == "0000000121032683"

    def test_output_format_urn(self) -> None:
        paxman.register_all_shipped()
        contract = ISNICapability.create_contract(output_format="urn")
        result = paxman.canonicalize("0000000121032683", contract)

        assert result.status == Resolution.SUCCESS
        assert result.canonicalized_value == "urn:isni:0000000121032683"

    def test_output_format_unknown_raises(self) -> None:
        with pytest.raises(ContractError):
            ISNICapability.create_contract(output_format="hyphenated")


class TestISNIPipelineReject:
    """§9 INVALID / MISSING rows plus multi-mention and temporal gates."""

    @pytest.mark.parametrize(
        "text",
        [
            "0000000121032684",
            "0000000122819550",
        ],
    )
    def test_bad_check_invalid(self, text: str) -> None:
        paxman.register_all_shipped()
        contract = ISNICapability.create_contract()
        result = paxman.canonicalize(text, contract)

        assert result.status == Resolution.INVALID
        assert result.canonicalized_value is None

    @pytest.mark.parametrize(
        "text",
        [
            "ISNI0000000121032683",
            "0000  0001 2103 2683",
            "000000012103268",
            "00000001210326833",
            "not an isni",
        ],
    )
    def test_unclaimed_missing(self, text: str) -> None:
        paxman.register_all_shipped()
        contract = ISNICapability.create_contract()
        result = paxman.canonicalize(text, contract)

        assert result.status == Resolution.MISSING

    def test_two_distinct_raise(self) -> None:
        paxman.register_all_shipped()
        contract = ISNICapability.create_contract()
        with pytest.raises(MultipleMentionsError):
            paxman.canonicalize("0000000121032683 000000012146438X", contract)

    def test_year_filter_drops_rules(self) -> None:
        paxman.register_all_shipped()
        contract = ISNICapability.create_contract(year=2023)
        result = paxman.canonicalize("0000000121032683", contract)

        assert result.status == Resolution.INVALID

    def test_pinned_structure_rule_alone(self) -> None:
        paxman.register_all_shipped()
        contract = ISNICapability.create_contract(
            pinned_rules=("Section 4-isni-structure",)
        )
        result = paxman.canonicalize("0000000121032683", contract)

        assert result.status == Resolution.SUCCESS
        assert result.canonicalized_value == "0000 0001 2103 2683"
