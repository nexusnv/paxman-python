"""Tests for ORCID rules (ISO 27729:2024 + Annex A MOD 11-2)."""

from __future__ import annotations

import pathlib

import pytest

from paxman.capabilities.ORCID.contract import ORCIDContract
from paxman.capabilities.ORCID.notation import ORCIDNotation
from paxman.capabilities.ORCID.rules.iso_27729_ed2024 import (
    PUBLICATION,
    Section4OrcidStructure,
    SectionAnnexAMod11Dash2,
)
from paxman.core.domain import RuleStrategy

pytestmark = [pytest.mark.capability]

VALID = [
    "0000-0002-1825-0097",
    "0000-0002-1694-233X",
    "0000-0001-5109-3700",
    "0000-0001-2281-955X",  # python-stdnum ISNI docstring vector
]


def _notation(hyphenated: str) -> ORCIDNotation:
    compact = hyphenated.replace("-", "").upper()
    h = compact[:4] + "-" + compact[4:8] + "-" + compact[8:12] + "-" + compact[12:]
    return ORCIDNotation(
        compact=compact,
        hyphenated=h,
        uri=f"https://orcid.org/{h}",
        check=compact[-1],
        is_uri="false",
    )


@pytest.mark.parametrize("rule_cls", [Section4OrcidStructure, SectionAnnexAMod11Dash2])
class TestBothRulesConjunction:
    """Both classes validate the FULL structure+checksum conjunction."""

    def test_valid_match(self, rule_cls: type) -> None:
        rule = rule_cls()
        contract = ORCIDContract()
        for h in VALID:
            assert rule.matches(_notation(h), contract) is True, h

    def test_bad_checksum_rejects(self, rule_cls: type) -> None:
        rule = rule_cls()
        contract = ORCIDContract()
        # Correct shape, wrong check digit (expected 7, given 8).
        assert rule.matches(_notation("0000-0002-1825-0098"), contract) is False

    def test_wrong_length_rejects(self, rule_cls: type) -> None:
        rule = rule_cls()
        contract = ORCIDContract()
        short = ORCIDNotation(
            compact="0000000218250090"[:15],
            hyphenated="0000-0002-1825-009",
            uri="",
            check="9",
            is_uri="false",
        )
        assert rule.matches(short, contract) is False

    def test_non_digit_base_rejects(self, rule_cls: type) -> None:
        rule = rule_cls()
        contract = ORCIDContract()
        bad = ORCIDNotation(
            compact="000X000218250097",
            hyphenated="000X-0002-1825-0097",
            uri="",
            check="7",
            is_uri="false",
        )
        assert rule.matches(bad, contract) is False

    def test_normalize_hyphenated_upper(self, rule_cls: type) -> None:
        rule = rule_cls()
        contract = ORCIDContract()
        n = _notation("0000-0002-1694-233x")
        assert rule.normalize(n, contract) == "0000-0002-1694-233X"

    def test_normalize_agreement(self, rule_cls: type) -> None:
        """Both rules normalize identically (candidate dedup stays SUCCESS)."""
        rule_a = Section4OrcidStructure()
        rule_b = SectionAnnexAMod11Dash2()
        contract = ORCIDContract()
        n = _notation("0000-0002-1825-0097")
        assert rule_a.normalize(n, contract) == rule_b.normalize(n, contract)


class TestProvenanceAndConventions:
    def setup_method(self) -> None:
        self.rule = Section4OrcidStructure()

    def test_publication(self) -> None:
        assert PUBLICATION.authority == "ISO"
        assert PUBLICATION.specification_name == "ISO 27729:2024"
        assert PUBLICATION.kind == "specification"
        assert PUBLICATION.reference_url == "https://www.iso.org/standard/87177.html"
        assert PUBLICATION.version == "2024-11"
        assert PUBLICATION.lifecycle == "active"
        assert PUBLICATION.publication_year == 2024

    def test_names_strategies_semantics(self) -> None:
        a = Section4OrcidStructure()
        b = SectionAnnexAMod11Dash2()
        assert a.name == "Section 4-orcid-structure"
        assert b.name == "Section A-mod11-2-check-character"
        for rule in (a, b):
            assert rule.strategy == RuleStrategy.PARSER
            assert rule.provenance == PUBLICATION
            assert rule.target_semantics == frozenset({"orcid_recognition"})
            assert rule.requires_features == frozenset()
            assert isinstance(rule.citation, str) and rule.citation != ""

    def test_distinct_citations(self) -> None:
        assert Section4OrcidStructure().citation != SectionAnnexAMod11Dash2().citation

    @pytest.mark.parametrize(
        "rule_cls", [Section4OrcidStructure, SectionAnnexAMod11Dash2]
    )
    def test_no_output_format_token(self, rule_cls: type) -> None:
        path = (
            pathlib.Path(__file__).resolve().parents[3]
            / "paxman"
            / "capabilities"
            / "ORCID"
            / "rules"
            / "iso_27729_ed2024.py"
        )
        text = path.read_text(encoding="utf-8")
        assert "output_format" not in text
