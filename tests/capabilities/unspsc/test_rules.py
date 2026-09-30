"""Tests for UNSPSC rules (UNGM structure, UNDP codeset, UNECE BFI)."""

import pytest

from paxman.capabilities.UNSPSC.contract import UNSPSCContract
from paxman.capabilities.UNSPSC.notation import UNSPSCNotation
from paxman.capabilities.UNSPSC.rules.undp_unspsc_codeset_ed2026 import (
    Section3CodesetMembership,
)
from paxman.capabilities.UNSPSC.rules.undp_unspsc_structure_ed2025 import (
    Section1HierarchyStructure,
    Section2LevelPadding,
)
from paxman.capabilities.UNSPSC.rules.unece_bfi_ed2005 import (
    Section4BusinessFunctionSuffix,
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


@pytest.mark.capability
class TestSection3CodesetMembership:
    """Section 3-codeset-membership: stem + live ancestors in the snapshot."""

    def setup_method(self) -> None:
        self.rule = Section3CodesetMembership()
        self.contract = UNSPSCContract()

    def test_metadata(self) -> None:
        assert self.rule.name == "Section 3-codeset-membership"
        assert self.rule.strategy is RuleStrategy.LOOKUP_TABLE
        assert self.rule.target_semantics == frozenset({"unspsc_recognition"})
        assert self.rule.requires_features == frozenset()
        assert self.rule.provenance.kind == "registry"
        assert self.rule.provenance.version.startswith("UNGM live export")

    @pytest.mark.parametrize(
        "digits",
        [
            "44103103",
            "43211503",
            "10101501",
            "25101703",
            "43000000",
            "43210000",
            "43211500",
            "44121700",
        ],
    )
    def test_accepts_issued(self, digits: str) -> None:
        assert self.rule.matches(_notation(digits), self.contract) is True

    @pytest.mark.parametrize("digits", ["44103199", "99999999", "43111503"])
    def test_rejects_unissued(self, digits: str) -> None:
        assert self.rule.matches(_notation(digits), self.contract) is False

    def test_requires_live_ancestors(self) -> None:
        # Synthetic stem with a dead family ancestor: well-formed and
        # 8-digit but no live row for the stem or its ancestors.
        assert self.rule.matches(_notation("43991503"), self.contract) is False

    def test_normalize_returns_stem(self) -> None:
        assert self.rule.normalize(_notation("44103103"), self.contract) == "44103103"


@pytest.mark.capability
class TestSection4BusinessFunctionSuffix:
    """Section 4-business-function-suffix: informative-only suffix lane."""

    def setup_method(self) -> None:
        self.rule = Section4BusinessFunctionSuffix()
        self.contract = UNSPSCContract()

    def test_metadata(self) -> None:
        assert self.rule.name == "Section 4-business-function-suffix"
        assert self.rule.strategy is RuleStrategy.PARSER
        assert self.rule.target_semantics == frozenset({"unspsc_recognition"})
        assert self.rule.requires_features == frozenset({"include_business_function"})
        assert (
            self.rule.provenance.authority
            == "United Nations Economic Commission for Europe"
        )
        assert self.rule.provenance.kind == "specification"
        assert self.rule.provenance.version == "v2.04"

    @pytest.mark.parametrize("function", ["00", "14", "99"])
    def test_passes_any_suffix(self, function: str) -> None:
        notation = _notation("44103103", 10, function)
        assert self.rule.matches(notation, self.contract) is True

    @pytest.mark.parametrize(
        ("digits", "native_length"),
        [("44103103", 8), ("44121700", 6)],
    )
    def test_ignores_short_lanes(self, digits: str, native_length: int) -> None:
        notation = _notation(digits, native_length)
        assert self.rule.matches(notation, self.contract) is True

    def test_rejects_malformed_suffix(self) -> None:
        notation = _notation("44103103", 10, "1")
        assert self.rule.matches(notation, self.contract) is False

    def test_normalize_returns_stem(self) -> None:
        notation = _notation("44103103", 10, "14")
        assert self.rule.normalize(notation, self.contract) == "44103103"
