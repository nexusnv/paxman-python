"""Tests for ISIN rules (ISO 6166:2021 PARSER + ANNA Guidelines LOOKUP_TABLE)."""

from __future__ import annotations

from pathlib import Path

import pytest

from paxman.capabilities.ISIN.contract import ISINContract
from paxman.capabilities.ISIN.notation import ISINNotation
from paxman.capabilities.ISIN.rules.anna_isin_guidelines_ed2025 import (
    Section5CountryAndSpecialPrefix,
)
from paxman.capabilities.ISIN.rules.iso_6166_ed2021 import (
    Section4IsinStructureCheckDigit,
)
from paxman.core.domain import RuleStrategy


def _notation(compact: str) -> ISINNotation:
    """Build a structurally decomposed notation from a 12-char compact string."""
    return ISINNotation(
        country_code=compact[0:2],
        nsin=compact[2:11],
        check_digit=compact[11],
        compact=compact,
    )


def _expand(compact: str) -> str:
    """Letter-expand a compact ISIN (A=10 ... Z=35), independent oracle."""
    out: list[str] = []
    for ch in compact:
        if ch.isdigit():
            out.append(ch)
        else:
            out.append(str(ord(ch) - 55))
    return "".join(out)


@pytest.mark.capability
class TestSection4IsinStructureCheckDigit:
    """PARSER rule: ISO 6166:2021 structure + expanded-string Luhn."""

    def setup_method(self) -> None:
        self.rule = Section4IsinStructureCheckDigit()
        self.contract = ISINContract()

    @pytest.mark.parametrize(
        "compact",
        [
            "US0378331005",
            "AU0000XVGZA3",
            "GB0002634946",
            "XS0931417173",
            "XTV15WLZJMF0",
        ],
    )
    def test_parser_valid(self, compact: str) -> None:
        assert self.rule.matches(_notation(compact), self.contract) is True

    def test_parser_bad_checksum(self) -> None:
        assert self.rule.matches(_notation("US0378331003"), self.contract) is False

    def test_flaw_pair_both_valid(self) -> None:
        # Adjacent-letter transposition preserves modulus-10: algorithm
        # limitation, documented, never corrected — both spellings validate.
        assert self.rule.matches(_notation("AU0000XVGZA3"), self.contract) is True
        assert self.rule.matches(_notation("AU0000VXGZA3"), self.contract) is True

    def test_z35_expansion(self) -> None:
        # Z must expand to two digits "35": pin the expansion independently,
        # then require the expanded-string Luhn total to be 0 mod 10.
        assert _expand("AU0000XVGZA3") == "1030000033311635103"
        expanded = _expand("AU0000XVGZA3")
        total = 0
        for i, digit in enumerate(reversed(expanded)):
            value = int(digit)
            if i % 2 == 1:
                value *= 2
                if value > 9:
                    value -= 9
            total += value
        assert total % 10 == 0
        assert self.rule.matches(_notation("AU0000XVGZA3"), self.contract) is True

    def test_normalize_returns_compact(self) -> None:
        notation = _notation("US0378331005")
        assert self.rule.normalize(notation, self.contract) == "US0378331005"


@pytest.mark.capability
class TestSection5CountryAndSpecialPrefix:
    """LOOKUP_TABLE rule: ISO 3166-1 alpha-2 plus ANNA special prefixes."""

    def setup_method(self) -> None:
        self.rule = Section5CountryAndSpecialPrefix()
        self.contract = ISINContract()

    @pytest.mark.parametrize("compact", ["US0378331005", "GB0002634946"])
    def test_lookup_valid_iso_prefixes(self, compact: str) -> None:
        assert self.rule.matches(_notation(compact), self.contract) is True

    @pytest.mark.parametrize(
        "compact", ["XS0931417173", "XTV15WLZJMF0", "US0378331005"]
    )
    def test_lookup_valid_prefixes(self, compact: str) -> None:
        # XS (international) and XT (digital tokens) are special prefixes;
        # US is ISO 3166-1. EZ/XK membership is pinned via country_code below.
        assert self.rule.matches(_notation(compact), self.contract) is True

    def test_lookup_valid_ez_xk_prefixes(self) -> None:
        # Check digits computed for the EZ/XK bases (mod-10 Double-Add-Double).
        assert self.rule.matches(_notation("EZ0378331006"), self.contract) is True
        assert self.rule.matches(_notation("XK0378331000"), self.contract) is True

    def test_lookup_rejects_bad_checksum(self) -> None:
        # Valid US prefix but broken check digit: neither rule matches, so
        # the pipeline reports INVALID (not SUCCESS via this rule alone).
        assert self.rule.matches(_notation("US0378331003"), self.contract) is False

    @pytest.mark.parametrize("compact", ["XX0378331005", "ZZ0378331001"])
    def test_lookup_rejects_isolations(self, compact: str) -> None:
        # Checksum-valid isolations (verified via stdnum oracle): rejection
        # rests on prefix membership alone, not on the check digit.
        parser = Section4IsinStructureCheckDigit()
        assert parser.matches(_notation(compact), self.contract) is True
        assert self.rule.matches(_notation(compact), self.contract) is False

    def test_lookup_rejects_qw(self) -> None:
        notation = ISINNotation(
            country_code="QW", nsin="07833100", check_digit="5", compact="QW078331005"
        )
        assert self.rule.matches(notation, self.contract) is False

    def test_lookup_rejects_inconsistent_decomposition(self) -> None:
        # Direct-call robustness: fields disagree with compact (valid compact,
        # unrelated decomposition) — the PARSER rejects this via its
        # consistency check, so the LOOKUP must too.
        notation = ISINNotation(
            country_code="US",
            nsin="000000000",
            check_digit="0",
            compact="US0378331005",
        )
        assert self.rule.matches(notation, self.contract) is False

    def test_normalize_returns_compact(self) -> None:
        notation = _notation("GB0002634946")
        assert self.rule.normalize(notation, self.contract) == "GB0002634946"


@pytest.mark.capability
class TestISINRuleAgreement:
    """Both rules agree on the canonical compact form."""

    def test_normalize_agreement(self) -> None:
        contract = ISINContract()
        parser = Section4IsinStructureCheckDigit()
        lookup = Section5CountryAndSpecialPrefix()
        for compact in ("US0378331005", "GB0002634946", "XS0931417173"):
            notation = _notation(compact)
            assert parser.normalize(notation, contract) == compact
            assert lookup.normalize(notation, contract) == compact

    def test_provenance_attrs(self) -> None:
        parser = Section4IsinStructureCheckDigit()
        assert parser.provenance.authority == "ISO"
        assert parser.provenance.specification_name == "ISO 6166:2021"
        assert "78502" in parser.provenance.reference_url
        assert parser.provenance.publication_year == 2021
        assert parser.provenance.kind == "specification"
        assert parser.provenance.lifecycle == "active"
        lookup = Section5CountryAndSpecialPrefix()
        assert lookup.provenance.authority == "ANNA"
        assert "Guidelines" in lookup.provenance.specification_name
        assert "V25" in (lookup.provenance.version or "")
        assert lookup.provenance.kind == "policy"
        assert lookup.provenance.publication_year == 2025

    def test_strategy_six_attrs(self) -> None:
        parser = Section4IsinStructureCheckDigit()
        lookup = Section5CountryAndSpecialPrefix()
        for rule in (parser, lookup):
            assert rule.name.startswith("Section ")
            assert isinstance(rule.strategy, RuleStrategy)
            assert isinstance(rule.provenance.publication_year, int)
            assert isinstance(rule.citation, str) and rule.citation
            assert rule.target_semantics and isinstance(
                rule.target_semantics, frozenset
            )
            assert isinstance(rule.requires_features, frozenset)
        assert Section4IsinStructureCheckDigit().strategy is RuleStrategy.PARSER
        assert Section5CountryAndSpecialPrefix().strategy is RuleStrategy.LOOKUP_TABLE
        assert Section4IsinStructureCheckDigit().name == (
            "Section 4-isin-structure-check-digit"
        )
        assert Section5CountryAndSpecialPrefix().name == (
            "Section 5-country-and-special-prefix"
        )

    def test_no_output_format_token(self) -> None:
        rules_dir = Path(__file__).resolve().parents[3]
        for rel in (
            "paxman/capabilities/ISIN/rules/iso_6166_ed2021.py",
            "paxman/capabilities/ISIN/rules/anna_isin_guidelines_ed2025.py",
        ):
            text = (rules_dir / rel).read_text(encoding="utf-8")
            assert "output_format" not in text, rel


@pytest.mark.capability
def test_prefix_sets_present() -> None:
    """Task 4: ISIN prefix data tables are importable and complete."""
    from paxman.capabilities.ISIN.rules.data.country_codes import (
        ISO_3166_1_ALPHA_2,
        SPECIAL_PREFIXES,
    )

    required_special = {
        "EU",
        "XS",
        "EZ",
        "XT",
        "XA",
        "XB",
        "XC",
        "XD",
        "XF",
        "XK",
        "QS",
        "QT",
    }
    assert required_special <= set(SPECIAL_PREFIXES)
    # QW excluded: not an allocated ISIN prefix (user-assigned QM-QZ minus QW).
    assert "QW" not in SPECIAL_PREFIXES
    assert "QW" not in ISO_3166_1_ALPHA_2
    # ZZ provisional: excluded from v1 so the lookup rule rejects it
    # (Task 5 isolation test ZZ0378331001 → INVALID).
    assert "ZZ" not in SPECIAL_PREFIXES
    assert "ZZ" not in ISO_3166_1_ALPHA_2
    # ISO set is the 249 ISO-assigned alpha-2 codes (XK is user-assigned,
    # owned by SPECIAL_PREFIXES).
    assert len(ISO_3166_1_ALPHA_2) == 249
    assert "XK" not in ISO_3166_1_ALPHA_2
