"""Tests for ISNI rules (ISO 27729:2024)."""

import pytest

from paxman.capabilities.ISNI.contract import ISNIContract
from paxman.capabilities.ISNI.notation import ISNINotation
from paxman.capabilities.ISNI.rules.iso_27729_ed2024 import (
    Section4IsniStructure,
    SectionAMod11Dash2,
)
from paxman.core.domain import RuleStrategy


def _notation(compact: str) -> ISNINotation:
    spaced = f"{compact[:4]} {compact[4:8]} {compact[8:12]} {compact[12:]}"
    return ISNINotation(
        compact=compact,
        spaced=spaced,
        uri=f"https://isni.org/isni/{compact}",
        check=compact[-1],
        is_uri="false",
    )


@pytest.mark.capability
class TestSection4IsniStructure:
    """Section 4-isni-structure: 16-char shape, ASCII digits + check char."""

    def setup_method(self) -> None:
        self.rule = Section4IsniStructure()
        self.contract = ISNIContract()

    def test_metadata(self) -> None:
        assert self.rule.name == "Section 4-isni-structure"
        assert self.rule.strategy is RuleStrategy.PARSER
        assert self.rule.target_semantics == frozenset({"isni_recognition"})
        assert self.rule.requires_features == frozenset()
        assert self.rule.provenance.publication_year == 2024
        assert self.rule.provenance.specification_name == "ISO 27729:2024"

    @pytest.mark.parametrize(
        "compact",
        [
            "0000000121032683",
            "000000012281955X",
            "000000012146438X",
            "0000000121241960",
            "0000000122974701",
        ],
    )
    def test_valid_vectors(self, compact: str) -> None:
        assert self.rule.matches(_notation(compact), self.contract) is True
        assert self.rule.normalize(_notation(compact), self.contract) == (
            f"{compact[:4]} {compact[4:8]} {compact[8:12]} {compact[12:]}"
        )

    @pytest.mark.parametrize(
        "compact",
        [
            "000000012103268",  # short
            "00000001210326833",  # long
            "0000000121032684",  # bad check
            "000000012103268x",  # lowercase check unclaimed by grammar
            "00000001210326X8",  # X mid-run
        ],
    )
    def test_invalid_vectors(self, compact: str) -> None:
        assert self.rule.matches(_notation(compact), self.contract) is False


@pytest.mark.capability
class TestSectionAMod11Dash2:
    """Section A-mod11-2-check-character: MOD 11-2 over the first 15 digits."""

    def setup_method(self) -> None:
        self.rule = SectionAMod11Dash2()
        self.contract = ISNIContract()

    def test_metadata(self) -> None:
        assert self.rule.name == "Section A-mod11-2-check-character"
        assert self.rule.strategy is RuleStrategy.PARSER
        assert self.rule.target_semantics == frozenset({"isni_recognition"})
        assert self.rule.requires_features == frozenset()
        assert self.rule.provenance.publication_year == 2024

    @pytest.mark.parametrize(
        "compact",
        [
            "0000000121032683",
            "000000012281955X",
            "000000012146438X",
            "0000000121241960",
            "1422458635730476",
        ],
    )
    def test_valid_vectors(self, compact: str) -> None:
        assert self.rule.matches(_notation(compact), self.contract) is True
        assert self.rule.normalize(_notation(compact), self.contract) == (
            f"{compact[:4]} {compact[4:8]} {compact[8:12]} {compact[12:]}"
        )

    @pytest.mark.parametrize(
        "compact",
        [
            "0000000121032684",
            "0000000122819550",
            "000000012103268",
        ],
    )
    def test_invalid_vectors(self, compact: str) -> None:
        assert self.rule.matches(_notation(compact), self.contract) is False
