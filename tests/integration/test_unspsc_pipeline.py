"""Integration tests for the UNSPSC capability through the full pipeline.

Resolution-state map: research `2026-09-30-unspsc-canonicalization.md` §9.
Every vector below was executed against the pipeline
(`register_all_shipped` + `canonicalize`); statuses are observed, not assumed.
"""

from __future__ import annotations

from collections.abc import Iterator

import pytest

import paxman
from paxman.capabilities.UNSPSC.capability import UNSPSCCapability
from paxman.core.discovery import reset_registry
from paxman.core.domain import Resolution
from paxman.core.errors import MultipleMentionsError


@pytest.fixture(autouse=True)
def _clean_registry() -> Iterator[None]:
    """Reset the capability registry before and after each test."""
    reset_registry()
    yield
    reset_registry()


@pytest.mark.integration
class TestUNSPSCSuccess:
    """Valid commodity/parent/alias/label/MDM/BFI inputs resolve SUCCESS."""

    @pytest.mark.parametrize(
        ("text", "expected"),
        [
            ("44103103", "44103103"),
            ("43211503", "43211503"),
            ("10101501", "10101501"),
            ("25101703", "25101703"),
            ("43000000", "43000000"),
            ("43210000", "43210000"),
            ("43211500", "43211500"),
            ("441217", "44121700"),
            ("UNSPSC 44103103", "44103103"),
            ("UNSPSC: 44103103", "44103103"),
            ("UNSPSC000.44103103", "44103103"),
            ("unspsc,43211509", "43211509"),
            ("4410310314", "44103103"),
            ("Printers (44103103) approved", "44103103"),
        ],
    )
    def test_success_rows(self, text: str, expected: str) -> None:
        paxman.register_all_shipped()
        contract = UNSPSCCapability.create_contract()
        result = paxman.canonicalize(text, contract)
        assert result.status == Resolution.SUCCESS
        assert result.canonicalized_value == expected

    def test_label_vs_bare_dedups_to_one(self) -> None:
        paxman.register_all_shipped()
        contract = UNSPSCCapability.create_contract()
        result = paxman.canonicalize("44103103 (UNSPSC 44103103)", contract)
        assert result.status == Resolution.SUCCESS
        assert result.canonicalized_value == "44103103"

    def test_span_bearing_match(self) -> None:
        paxman.register_all_shipped()
        contract = UNSPSCCapability.create_contract()
        result = paxman.canonicalize("see UNSPSC 44103103 (Printers)", contract)
        assert result.status == Resolution.SUCCESS
        assert result.span == (4, 19)

    def test_output_formats(self) -> None:
        paxman.register_all_shipped()
        assert (
            paxman.canonicalize(
                "44103103",
                UNSPSCCapability.create_contract(output_format="labeled"),
            ).canonicalized_value
            == "UNSPSC 44103103"
        )
        assert (
            paxman.canonicalize(
                "441217", UNSPSCCapability.create_contract(output_format="native")
            ).canonicalized_value
            == "441217"
        )
        assert (
            paxman.canonicalize(
                "4410310314", UNSPSCCapability.create_contract(output_format="native")
            ).canonicalized_value
            == "4410310314"
        )

    def test_determinism(self) -> None:
        paxman.register_all_shipped()
        contract = UNSPSCCapability.create_contract()
        first = paxman.canonicalize("UNSPSC 44103103", contract)
        second = paxman.canonicalize("UNSPSC 44103103", contract)
        assert first.status == second.status == Resolution.SUCCESS
        assert first.canonicalized_value == second.canonicalized_value == "44103103"
        assert first.version_stamp == second.version_stamp


@pytest.mark.integration
class TestUNSPSCMissing:
    """Unclaimed surfaces resolve MISSING (grammar never fires)."""

    @pytest.mark.parametrize(
        "text",
        [
            "43 21 15 03",
            "43.21.15.03",
            "4410-3103",
            "43",
            "4321",
            "4410310",
            "441031031",
            "scaffold probe",
            "",
        ],
    )
    def test_missing_rows(self, text: str) -> None:
        paxman.register_all_shipped()
        contract = UNSPSCCapability.create_contract()
        result = paxman.canonicalize(text, contract)
        assert result.status == Resolution.MISSING


@pytest.mark.integration
class TestUNSPSCInvalid:
    """Claimed but rejected inputs resolve INVALID (rule veto)."""

    @pytest.mark.parametrize(
        "text",
        [
            "43001503",
            "00101501",
            "44103199",
            "99999999",
            "11101803",
        ],
    )
    def test_invalid_rows(self, text: str) -> None:
        # "11101803" (Wikidata-cited platinum) is absent from the pinned
        # UNGM-export snapshot, so it is INVALID under this snapshot by
        # design — not a claim about the full UNDP codeset.
        paxman.register_all_shipped()
        contract = UNSPSCCapability.create_contract()
        result = paxman.canonicalize(text, contract)
        assert result.status == Resolution.INVALID

    def test_bfi_gated_off_drops_suffix_candidate(self) -> None:
        # Dropping Section 4 removes its candidate/provenance but the stem
        # is still validated by Sections 1-3, so the verdict stays SUCCESS
        # (ISBN include_range_validation precedent — corroborating-rule
        # gating changes provenance, not the verdict).
        paxman.register_all_shipped()
        contract = UNSPSCCapability.create_contract(include_business_function=False)
        result = paxman.canonicalize("4410310314", contract)
        assert result.status == Resolution.SUCCESS
        assert result.canonicalized_value == "44103103"
        assert all(
            c.validation_rule != "Section 4-business-function-suffix"
            for c in result.candidates
        )
        assert any(
            c.validation_rule == "Section 4-business-function-suffix"
            for c in paxman.canonicalize(
                "4410310314", UNSPSCCapability.create_contract()
            ).candidates
        )


@pytest.mark.integration
class TestUNSPSCAmbiguity:
    """Two distinct stems in one slice raise MultipleMentionsError."""

    def test_two_distinct_raise(self) -> None:
        paxman.register_all_shipped()
        contract = UNSPSCCapability.create_contract()
        with pytest.raises(MultipleMentionsError):
            paxman.canonicalize("44103103, 43211503", contract)
