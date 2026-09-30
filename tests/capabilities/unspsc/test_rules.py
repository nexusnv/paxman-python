"""Tests for UNSPSC rules (UNGM structure, UNDP codeset, UNECE BFI)."""

import pytest

from paxman.capabilities.UNSPSC.contract import UNSPSCContract
from paxman.capabilities.UNSPSC.notation import UNSPSCNotation
from paxman.capabilities.UNSPSC.rules.undp_unspsc_structure_ed2025 import (
    Section1HierarchyStructure,
    Section2LevelPadding,
)
from paxman.core.domain import RuleStrategy


def _notation(
    digits: str, native_length: int = 8, function: str = ""
) -> UNSPSCNotation:
    if digits.endswith("000000"):
        level = "segment"
    elif digits.endswith("0000"):
        level = "family"
    elif digits.endswith("00"):
        level = "class"
    else:
        level = "commodity"
    return UNSPSCNotation(
        digits=digits, level=level, function=function, native_length=native_length
    )


@pytest.mark.capability
class TestSection1HierarchyStructure:
    """Section 1-hierarchy-structure: 6/8/10 lane, ASCII digits."""

    def setup_method(self) -> None:
        self.rule = Section1HierarchyStructure()
        self.contract = UNSPSCContract()

    def test_metadata(self) -> None:
        assert self.rule.name == "Section 1-hierarchy-structure"
        assert self.rule.strategy is RuleStrategy.PARSER
        assert self.rule.target_semantics == frozenset({"unspsc_recognition"})
        assert self.rule.requires_features == frozenset()
        assert self.rule.provenance.authority == "United Nations Development Programme"
        assert self.rule.provenance.kind == "specification"
        assert self.rule.provenance.version == "2025-07-08"
        assert self.rule.provenance.publication_year == 2025

    @pytest.mark.parametrize(
        ("digits", "native_length", "function"),
        [
            ("44103103", 8, ""),
            ("43000000", 8, ""),
            ("44121700", 6, ""),
            ("44103103", 10, "14"),
        ],
    )
    def test_accepts_lanes(
        self, digits: str, native_length: int, function: str
    ) -> None:
        notation = _notation(digits, native_length, function)
        assert self.rule.matches(notation, self.contract) is True

    @pytest.mark.parametrize(
        ("digits", "native_length", "function"),
        [
            ("4410310", 7, ""),
            ("441031", 6, ""),
            ("44103103", 8, "1"),
            ("44103A03", 8, ""),
        ],
    )
    def test_rejects_bad_shapes(
        self, digits: str, native_length: int, function: str
    ) -> None:
        notation = _notation(digits, native_length, function)
        assert self.rule.matches(notation, self.contract) is False

    def test_normalize_returns_stem(self) -> None:
        assert (
            self.rule.normalize(_notation("44121700", 6), self.contract) == "44121700"
        )
        assert (
            self.rule.normalize(_notation("44103103", 10, "14"), self.contract)
            == "44103103"
        )


@pytest.mark.capability
class TestSection2LevelPadding:
    """Section 2-level-padding: 00-pair lattice consistency."""

    def setup_method(self) -> None:
        self.rule = Section2LevelPadding()
        self.contract = UNSPSCContract()

    def test_metadata(self) -> None:
        assert self.rule.name == "Section 2-level-padding"
        assert self.rule.strategy is RuleStrategy.PARSER
        assert self.rule.target_semantics == frozenset({"unspsc_recognition"})
        assert self.rule.requires_features == frozenset()
        assert self.rule.provenance is Section1HierarchyStructure.provenance

    @pytest.mark.parametrize(
        "digits",
        ["43000000", "43210000", "43211500", "43211503", "44103103", "10101501"],
    )
    def test_accepts_lattice(self, digits: str) -> None:
        assert self.rule.matches(_notation(digits), self.contract) is True

    @pytest.mark.parametrize("digits", ["43001503", "00101501"])
    def test_rejects_mid_zero(self, digits: str) -> None:
        assert self.rule.matches(_notation(digits), self.contract) is False

    def test_wellformed_unissued_passes_padding(self) -> None:
        # "43111503" is lattice-consistent; unissued-ness is Section 3's job.
        assert self.rule.matches(_notation("43111503"), self.contract) is True

    def test_normalize_returns_stem(self) -> None:
        assert self.rule.normalize(_notation("43211503"), self.contract) == "43211503"
