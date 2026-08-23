"""Tests for Country capability validation rules."""

from __future__ import annotations

import pytest

from paxman.capabilities.Country.contract import CountryContract
from paxman.capabilities.Country.notation import CountryNotation
from paxman.capabilities.Country.rules.cldr_localized_ed2025 import (
    SectionLocalizedNames,
)
from paxman.capabilities.Country.rules.iso_3166_ed2024 import (
    SectionAlpha2Codes,
    SectionAlpha3Codes,
    SectionNames,
    SectionNumericCodes,
)
from paxman.capabilities.Country.rules.iso_3166_historical_ed2020 import (
    SectionHistoricalNames,
)
from paxman.core.domain import RuleStrategy

pytestmark = [pytest.mark.capability, pytest.mark.country]


class TestSectionAlpha2Codes:
    """Tests for SectionAlpha2Codes rule."""

    def setup_method(self) -> None:
        self.rule = SectionAlpha2Codes()

    def test_matches_valid_alpha2(self) -> None:
        """Happy path: valid alpha-2 code matches."""
        contract = CountryContract()
        notation = CountryNotation(shape="alpha2", value="US")
        assert self.rule.matches(notation, contract) is True

    def test_matches_lowercase(self) -> None:
        """Edge case: lowercase alpha-2 matches."""
        contract = CountryContract()
        notation = CountryNotation(shape="alpha2", value="us")
        assert self.rule.matches(notation, contract) is True

    def test_rejects_wrong_shape(self) -> None:
        """Notation with wrong shape."""
        contract = CountryContract()
        notation = CountryNotation(shape="name", value="US")
        assert self.rule.matches(notation, contract) is False

    def test_rejects_invalid_code(self) -> None:
        """Notation with invalid alpha-2 code."""
        contract = CountryContract()
        notation = CountryNotation(shape="alpha2", value="ZZ")
        assert self.rule.matches(notation, contract) is False

    def test_rejects_historical_code(self) -> None:
        """Historical alpha-2 code (SU) is not in active set."""
        contract = CountryContract()
        notation = CountryNotation(shape="alpha2", value="SU")
        assert self.rule.matches(notation, contract) is False

    def test_normalize_produces_canonical(self) -> None:
        """Verify exact canonical output."""
        contract = CountryContract()
        notation = CountryNotation(shape="alpha2", value="US")
        assert self.rule.normalize(notation, contract) == "US"

    @pytest.mark.parametrize("fmt", ["alpha3", "numeric", "name"])
    def test_normalize_ignores_output_format_returns_alpha2(self, fmt: str) -> None:
        """Rules emit the default alpha-2 canonical value, not the requested format."""
        contract = CountryContract(output_format=fmt)
        notation = CountryNotation(shape="alpha2", value="DE")
        assert self.rule.normalize(notation, contract) == "DE"

    def test_provenance_attributes(self) -> None:
        """Verify authority, spec name, year, lifecycle."""
        assert self.rule.provenance.authority == "ISO"
        assert self.rule.provenance.specification_name == "ISO 3166-1:2020"
        assert self.rule.provenance.publication_year == 2020
        assert self.rule.provenance.lifecycle == "active"

    def test_rule_name(self) -> None:
        """Verify name follows convention."""
        assert self.rule.name == "Section-alpha2-codes"

    def test_strategy(self) -> None:
        """Verify the rule strategy enum."""
        assert self.rule.strategy == RuleStrategy.LOOKUP_TABLE


class TestSectionAlpha3Codes:
    """Tests for SectionAlpha3Codes rule."""

    def setup_method(self) -> None:
        self.rule = SectionAlpha3Codes()

    def test_matches_valid_alpha3(self) -> None:
        """Happy path: valid alpha-3 code matches."""
        contract = CountryContract()
        notation = CountryNotation(shape="alpha3", value="USA")
        assert self.rule.matches(notation, contract) is True

    def test_matches_lowercase(self) -> None:
        """Edge case: lowercase alpha-3 matches."""
        contract = CountryContract()
        notation = CountryNotation(shape="alpha3", value="usa")
        assert self.rule.matches(notation, contract) is True

    def test_rejects_wrong_shape(self) -> None:
        """Notation with wrong shape."""
        contract = CountryContract()
        notation = CountryNotation(shape="name", value="USA")
        assert self.rule.matches(notation, contract) is False

    def test_rejects_invalid_code(self) -> None:
        """Notation with invalid alpha-3 code."""
        contract = CountryContract()
        notation = CountryNotation(shape="alpha3", value="ZZZ")
        assert self.rule.matches(notation, contract) is False

    def test_normalize_produces_canonical(self) -> None:
        """Verify exact canonical output."""
        contract = CountryContract()
        notation = CountryNotation(shape="alpha3", value="USA")
        assert self.rule.normalize(notation, contract) == "US"

    @pytest.mark.parametrize("fmt", ["alpha3", "numeric", "name"])
    def test_normalize_ignores_output_format_returns_alpha2(self, fmt: str) -> None:
        """Rules emit the default alpha-2 canonical value, not the requested format."""
        contract = CountryContract(output_format=fmt)
        notation = CountryNotation(shape="alpha3", value="DEU")
        assert self.rule.normalize(notation, contract) == "DE"

    def test_provenance_attributes(self) -> None:
        """Verify authority, spec name, year, lifecycle."""
        assert self.rule.provenance.authority == "ISO"
        assert self.rule.provenance.specification_name == "ISO 3166-1:2020"
        assert self.rule.provenance.publication_year == 2020
        assert self.rule.provenance.lifecycle == "active"

    def test_rule_name(self) -> None:
        """Verify name follows convention."""
        assert self.rule.name == "Section-alpha3-codes"

    def test_strategy(self) -> None:
        """Verify the rule strategy enum."""
        assert self.rule.strategy == RuleStrategy.LOOKUP_TABLE


class TestSectionNumericCodes:
    """Tests for SectionNumericCodes rule."""

    def setup_method(self) -> None:
        self.rule = SectionNumericCodes()

    def test_matches_valid_numeric(self) -> None:
        """Happy path: valid numeric code matches."""
        contract = CountryContract()
        notation = CountryNotation(shape="numeric", value="840")
        assert self.rule.matches(notation, contract) is True

    def test_matches_with_leading_zeros(self) -> None:
        """Edge case: numeric code with leading zeros."""
        contract = CountryContract()
        notation = CountryNotation(shape="numeric", value="004")
        assert self.rule.matches(notation, contract) is True

    def test_rejects_wrong_shape(self) -> None:
        """Notation with wrong shape."""
        contract = CountryContract()
        notation = CountryNotation(shape="name", value="840")
        assert self.rule.matches(notation, contract) is False

    def test_rejects_invalid_code(self) -> None:
        """Notation with invalid numeric code."""
        contract = CountryContract()
        notation = CountryNotation(shape="numeric", value="000")
        assert self.rule.matches(notation, contract) is False

    def test_normalize_produces_canonical(self) -> None:
        """Verify exact canonical output."""
        contract = CountryContract()
        notation = CountryNotation(shape="numeric", value="840")
        assert self.rule.normalize(notation, contract) == "US"

    def test_normalize_leading_zeros(self) -> None:
        """Verify normalization with leading zeros."""
        contract = CountryContract()
        notation = CountryNotation(shape="numeric", value="004")
        assert self.rule.normalize(notation, contract) == "AF"

    @pytest.mark.parametrize("fmt", ["alpha3", "numeric", "name"])
    def test_normalize_ignores_output_format_returns_alpha2(self, fmt: str) -> None:
        """Rules emit the default alpha-2 canonical value, not the requested format."""
        contract = CountryContract(output_format=fmt)
        notation = CountryNotation(shape="numeric", value="276")
        assert self.rule.normalize(notation, contract) == "DE"

    def test_provenance_attributes(self) -> None:
        """Verify authority, spec name, year, lifecycle."""
        assert self.rule.provenance.authority == "ISO"
        assert self.rule.provenance.specification_name == "ISO 3166-1:2020"
        assert self.rule.provenance.publication_year == 2020
        assert self.rule.provenance.lifecycle == "active"

    def test_rule_name(self) -> None:
        """Verify name follows convention."""
        assert self.rule.name == "Section-numeric-codes"

    def test_strategy(self) -> None:
        """Verify the rule strategy enum."""
        assert self.rule.strategy == RuleStrategy.LOOKUP_TABLE


class TestSectionNames:
    """Tests for SectionNames rule."""

    def setup_method(self) -> None:
        self.rule = SectionNames()

    def test_matches_valid_name(self) -> None:
        """Happy path: valid country name matches."""
        contract = CountryContract()
        notation = CountryNotation(shape="name", value="UNITED STATES")
        assert self.rule.matches(notation, contract) is True

    def test_matches_lowercase(self) -> None:
        """Edge case: lowercase name matches."""
        contract = CountryContract()
        notation = CountryNotation(shape="name", value="united states")
        assert self.rule.matches(notation, contract) is True

    def test_rejects_wrong_shape(self) -> None:
        """Notation with wrong shape."""
        contract = CountryContract()
        notation = CountryNotation(shape="alpha2", value="UNITED STATES")
        assert self.rule.matches(notation, contract) is False

    def test_rejects_invalid_name(self) -> None:
        """Notation with invalid name."""
        contract = CountryContract()
        notation = CountryNotation(shape="name", value="NOT A COUNTRY")
        assert self.rule.matches(notation, contract) is False

    def test_normalize_produces_canonical(self) -> None:
        """Verify exact canonical output."""
        contract = CountryContract()
        notation = CountryNotation(shape="name", value="UNITED STATES")
        assert self.rule.normalize(notation, contract) == "US"

    def test_normalize_synonym_usa(self) -> None:
        """Verify USA synonym normalizes to US."""
        contract = CountryContract()
        notation = CountryNotation(shape="name", value="USA")
        assert self.rule.normalize(notation, contract) == "US"

    @pytest.mark.parametrize("fmt", ["alpha3", "numeric", "name"])
    def test_normalize_ignores_output_format_returns_alpha2(self, fmt: str) -> None:
        """Rules emit the default alpha-2 canonical value, not the requested format."""
        contract = CountryContract(output_format=fmt)
        notation = CountryNotation(shape="name", value="GERMANY")
        assert self.rule.normalize(notation, contract) == "DE"

    def test_normalize_synonym_ignores_output_format_returns_alpha2(self) -> None:
        """Synonym input still normalizes to the default alpha-2, not a name."""
        contract = CountryContract(output_format="name")
        notation = CountryNotation(shape="name", value="USA")
        assert self.rule.normalize(notation, contract) == "US"

    def test_matches_usa(self) -> None:
        """USA synonym matches SectionNames."""
        contract = CountryContract()
        notation = CountryNotation(shape="name", value="USA")
        assert self.rule.matches(notation, contract) is True
        assert self.rule.normalize(notation, contract) == "US"

    def test_matches_holland(self) -> None:
        """Holland matches as a Netherlands synonym."""
        contract = CountryContract()
        notation = CountryNotation(shape="name", value="Holland")
        assert self.rule.matches(notation, contract) is True

    def test_normalize_holland(self) -> None:
        """Holland normalizes to NL."""
        contract = CountryContract()
        notation = CountryNotation(shape="name", value="Holland")
        assert self.rule.normalize(notation, contract) == "NL"

    def test_normalize_cote_divoire(self) -> None:
        """Accented Côte d'Ivoire resolves to CI."""
        contract = CountryContract()
        notation = CountryNotation(shape="name", value="Côte d'Ivoire")
        assert self.rule.normalize(notation, contract) == "CI"

    def test_matches_ascii_official_alias(self) -> None:
        """ASCII official-name aliases resolve to the existing code."""
        contract = CountryContract()
        assert self.rule.matches(
            CountryNotation(shape="name", value="GREAT BRITAIN"), contract
        )
        assert (
            self.rule.normalize(
                CountryNotation(shape="name", value="GREAT BRITAIN"), contract
            )
            == "GB"
        )
        assert (
            self.rule.normalize(
                CountryNotation(shape="name", value="CZECH REPUBLIC"), contract
            )
            == "CZ"
        )

    def test_matches_spaced_variant(self) -> None:
        """Spaced abbreviation variant resolves to the existing code."""
        contract = CountryContract()
        notation = CountryNotation(shape="name", value="U S A")
        assert self.rule.matches(notation, contract) is True
        assert self.rule.normalize(notation, contract) == "US"

    def test_matches_cote_divoire_unaccented(self) -> None:
        """Unaccented Cote d'Ivoire resolves to CI via shared normalization."""
        contract = CountryContract()
        notation = CountryNotation(shape="name", value="Cote d'Ivoire")
        assert self.rule.matches(notation, contract) is True
        assert self.rule.normalize(notation, contract) == "CI"

    def test_matches_turkiye_with_and_without_accent(self) -> None:
        """Both accented and unaccented Turkiye forms resolve to TR."""
        contract = CountryContract()
        for value in ("TÜRKIYE", "TURKIYE"):
            notation = CountryNotation(shape="name", value=value)
            assert self.rule.matches(notation, contract) is True
            assert self.rule.normalize(notation, contract) == "TR"

    def test_defers_cldr_owned_key_when_localized_enabled(self) -> None:
        """A CLDR-owned normalized key is not ISO-validated when localized.

        "México" normalizes to "MEXICO", which also matches the ISO English
        short name "Mexico". Under the single-authority precedence policy the
        ISO rule defers to the CLDR rule while ``include_localized`` is
        enabled, so the localized name cannot also yield an ISO candidate.
        """
        contract = CountryContract(include_localized=True)
        notation = CountryNotation(shape="name", value="México")
        assert self.rule.matches(notation, contract) is False

    def test_validates_cldr_colliding_english_name_without_localized(self) -> None:
        """Without include_localized, the English name "Mexico" is ISO-owned."""
        contract = CountryContract()
        notation = CountryNotation(shape="name", value="Mexico")
        assert self.rule.matches(notation, contract) is True

    def test_matches_collapsed_whitespace_name(self) -> None:
        """Collapsed whitespace United Kingdom resolves to GB."""
        contract = CountryContract()
        notation = CountryNotation(shape="name", value="  United   Kingdom  ")
        assert self.rule.matches(notation, contract) is True
        assert self.rule.normalize(notation, contract) == "GB"

    def test_provenance_attributes(self) -> None:
        """Verify authority, spec name, year, lifecycle."""
        assert self.rule.provenance.authority == "ISO"
        assert self.rule.provenance.specification_name == "ISO 3166-1:2020"
        assert self.rule.provenance.publication_year == 2020
        assert self.rule.provenance.lifecycle == "active"

    def test_rule_name(self) -> None:
        """Verify name follows convention."""
        assert self.rule.name == "Section-names"

    def test_strategy(self) -> None:
        """Verify the rule strategy enum."""
        assert self.rule.strategy == RuleStrategy.LOOKUP_TABLE


class TestSectionHistoricalNames:
    """Tests for SectionHistoricalNames rule.

    Historical entities map to their own former alpha-2 codes:
      BURMA → BU (not MM)
      USSR  → SU (not RU)
    """

    def setup_method(self) -> None:
        self.rule = SectionHistoricalNames()

    def test_matches_when_enabled(self) -> None:
        """Happy path: historical enabled and name matches."""
        contract = CountryContract(include_historical=True)
        notation = CountryNotation(shape="name", value="BURMA")
        assert self.rule.matches(notation, contract) is True

    def test_matches_lowercase(self) -> None:
        """Edge case: lowercase historical name matches."""
        contract = CountryContract(include_historical=True)
        notation = CountryNotation(shape="name", value="burma")
        assert self.rule.matches(notation, contract) is True

    def test_matches_soviet_union(self) -> None:
        """Soviet Union alternate name matches."""
        contract = CountryContract(include_historical=True)
        notation = CountryNotation(shape="name", value="SOVIET UNION")
        assert self.rule.matches(notation, contract) is True

    def test_matches_validates_notation_ignoring_feature_flag(self) -> None:
        """matches() validates notation/table membership, not the feature flag.

        Activation when ``include_historical`` is False (the default) is
        engine-owned via ``requires_features``; matches() itself must still
        accept the notation.
        """
        contract = CountryContract()
        notation = CountryNotation(shape="name", value="BURMA")
        assert self.rule.matches(notation, contract) is True

    def test_accepts_historical_alpha2(self) -> None:
        """Now accepts alpha2 shape for historical codes (round-trip)."""
        contract = CountryContract(include_historical=True)
        # SU is a formerly used alpha-2 code (USSR)
        notation = CountryNotation(shape="alpha2", value="SU")
        assert self.rule.matches(notation, contract) is True

    def test_rejects_active_alpha2_as_historical(self) -> None:
        """Active alpha-2 codes rejected by historical rule."""
        contract = CountryContract(include_historical=True)
        notation = CountryNotation(shape="alpha2", value="US")
        assert self.rule.matches(notation, contract) is False

    def test_rejects_invalid_name(self) -> None:
        """Notation with invalid historical name."""
        contract = CountryContract(include_historical=True)
        notation = CountryNotation(shape="name", value="NOT A COUNTRY")
        assert self.rule.matches(notation, contract) is False

    def test_normalize_burma(self) -> None:
        """Burma normalizes to its own former code BU (not MM)."""
        contract = CountryContract(include_historical=True)
        notation = CountryNotation(shape="name", value="BURMA")
        assert self.rule.normalize(notation, contract) == "BU"

    def test_normalize_ussr(self) -> None:
        """USSR normalizes to its own former code SU (not RU)."""
        contract = CountryContract(include_historical=True)
        notation = CountryNotation(shape="name", value="USSR")
        assert self.rule.normalize(notation, contract) == "SU"

    def test_normalize_soviet_union(self) -> None:
        """Soviet Union normalizes to SU."""
        contract = CountryContract(include_historical=True)
        notation = CountryNotation(shape="name", value="SOVIET UNION")
        assert self.rule.normalize(notation, contract) == "SU"

    def test_normalize_historical_alpha2(self) -> None:
        """Historical alpha-2 code normalizes to itself (round-trip)."""
        contract = CountryContract(include_historical=True)
        notation = CountryNotation(shape="alpha2", value="SU")
        assert self.rule.normalize(notation, contract) == "SU"

    def test_normalize_czechoslovakia(self) -> None:
        """Czechoslovakia normalizes to CS."""
        contract = CountryContract(include_historical=True)
        notation = CountryNotation(shape="name", value="CZECHOSLOVAKIA")
        assert self.rule.normalize(notation, contract) == "CS"

    def test_normalize_east_germany(self) -> None:
        """East Germany normalizes to DD."""
        contract = CountryContract(include_historical=True)
        notation = CountryNotation(shape="name", value="EAST GERMANY")
        assert self.rule.normalize(notation, contract) == "DD"

    def test_matches_viet_cong(self) -> None:
        """Viet Cong matches the historical rule."""
        contract = CountryContract(include_historical=True)
        notation = CountryNotation(shape="name", value="VIET CONG")
        assert self.rule.matches(notation, contract) is True

    def test_normalize_viet_cong(self) -> None:
        """Viet Cong normalizes to its own former code VD (not VN)."""
        contract = CountryContract(include_historical=True)
        notation = CountryNotation(shape="name", value="VIET CONG")
        assert self.rule.normalize(notation, contract) == "VD"

    def test_matches_east_german(self) -> None:
        """East German alternate name matches the historical rule."""
        contract = CountryContract(include_historical=True)
        notation = CountryNotation(shape="name", value="EAST GERMAN")
        assert self.rule.matches(notation, contract) is True

    def test_normalize_gdr(self) -> None:
        """GDR normalizes to DD."""
        contract = CountryContract(include_historical=True)
        notation = CountryNotation(shape="name", value="GDR")
        assert self.rule.normalize(notation, contract) == "DD"

    def test_normalize_metropolitan_france(self) -> None:
        """Metropolitan France normalizes to FX."""
        contract = CountryContract(include_historical=True)
        notation = CountryNotation(shape="name", value="METROPOLITAN FRANCE")
        assert self.rule.normalize(notation, contract) == "FX"

    def test_matches_france_metropolitan(self) -> None:
        """Punctuated France, Metropolitan resolves to FX via normalization."""
        contract = CountryContract(include_historical=True)
        notation = CountryNotation(shape="name", value="France, Metropolitan")
        assert self.rule.matches(notation, contract) is True
        assert self.rule.normalize(notation, contract) == "FX"

    def test_matches_france_metropolitan_without_comma(self) -> None:
        """Punctuation-stripped France Metropolitan also resolves to FX."""
        contract = CountryContract(include_historical=True)
        notation = CountryNotation(shape="name", value="France Metropolitan")
        assert self.rule.matches(notation, contract) is True
        assert self.rule.normalize(notation, contract) == "FX"

    def test_normalize_ussr_soviet_socialist_republics(self) -> None:
        """USSR Soviet Socialist Republics normalizes to SU."""
        contract = CountryContract(include_historical=True)
        notation = CountryNotation(
            shape="name", value="USSR SOVIET SOCIALIST REPUBLICS"
        )
        assert self.rule.normalize(notation, contract) == "SU"

    def test_normalize_union_of_soviet_socialist_republics(self) -> None:
        """Union of Soviet Socialist Republics normalizes to SU."""
        contract = CountryContract(include_historical=True)
        notation = CountryNotation(
            shape="name", value="UNION OF SOVIET SOCIALIST REPUBLICS"
        )
        assert self.rule.normalize(notation, contract) == "SU"

    def test_normalize_peoples_democratic_republic_of_yemen(self) -> None:
        """Peoples Democratic Republic of Yemen normalizes to YD."""
        contract = CountryContract(include_historical=True)
        notation = CountryNotation(
            shape="name", value="PEOPLES DEMOCRATIC REPUBLIC OF YEMEN"
        )
        assert self.rule.normalize(notation, contract) == "YD"

    def test_matches_historical_numeric(self) -> None:
        """Historical numeric code matches when enabled."""
        contract = CountryContract(include_historical=True)
        notation = CountryNotation(shape="numeric", value="200")
        assert self.rule.matches(notation, contract) is True

    def test_matches_validates_numeric_notation_ignoring_feature_flag(self) -> None:
        """matches() validates numeric table membership, not the feature flag.

        Activation when ``include_historical`` is False (the default) is
        engine-owned via ``requires_features``; matches() itself must still
        accept the notation.
        """
        contract = CountryContract()
        notation = CountryNotation(shape="numeric", value="200")
        assert self.rule.matches(notation, contract) is True

    def test_normalize_historical_numeric(self) -> None:
        """Historical numeric code normalizes to former alpha-2 (always alpha2)."""
        contract = CountryContract(include_historical=True)
        notation = CountryNotation(shape="numeric", value="200")
        assert self.rule.normalize(notation, contract) == "CS"

    def test_normalize_historical_numeric_antilles(self) -> None:
        """Netherlands Antilles numeric code normalizes to AN."""
        contract = CountryContract(include_historical=True)
        notation = CountryNotation(shape="numeric", value="530")
        assert self.rule.normalize(notation, contract) == "AN"

    def test_historical_normalize_ignores_output_format(self) -> None:
        """Historical normalize always returns alpha-2 regardless of output_format."""
        contract = CountryContract(include_historical=True, output_format="alpha3")
        notation = CountryNotation(shape="name", value="USSR")
        # Historical always returns former alpha-2 code (SU), not converted to alpha-3
        assert self.rule.normalize(notation, contract) == "SU"

    def test_provenance_attributes(self) -> None:
        """Verify authority, spec name, year, lifecycle."""
        assert self.rule.provenance.authority == "ISO"
        assert self.rule.provenance.specification_name == "ISO 3166-3"
        assert self.rule.provenance.publication_year == 2020
        assert self.rule.provenance.lifecycle == "active"

    def test_rule_name(self) -> None:
        """Verify name follows convention."""
        assert self.rule.name == "Section-historical-names"

    def test_strategy(self) -> None:
        """Verify the rule strategy enum."""
        assert self.rule.strategy == RuleStrategy.LOOKUP_TABLE


class TestSectionLocalizedNames:
    """Tests for SectionLocalizedNames rule."""

    def setup_method(self) -> None:
        self.rule = SectionLocalizedNames()

    def test_matches_chinese_name(self) -> None:
        """Chinese localized name matches."""
        contract = CountryContract(include_localized=True)
        notation = CountryNotation(shape="name", value="马来西亚")
        assert self.rule.matches(notation, contract) is True

    def test_matches_validates_notation_ignoring_feature_flag(self) -> None:
        """matches() validates table membership, not the feature flag.

        Activation when ``include_localized`` is False (the default) is
        engine-owned via ``requires_features``; matches() itself must still
        accept the notation.
        """
        contract = CountryContract()
        notation = CountryNotation(shape="name", value="马来西亚")
        assert self.rule.matches(notation, contract) is True

    def test_rejects_wrong_shape(self) -> None:
        """Notation with wrong shape."""
        contract = CountryContract(include_localized=True)
        notation = CountryNotation(shape="alpha2", value="MY")
        assert self.rule.matches(notation, contract) is False

    def test_normalize_malaysia(self) -> None:
        """马来西亚 normalizes to MY."""
        contract = CountryContract(include_localized=True)
        notation = CountryNotation(shape="name", value="马来西亚")
        assert self.rule.normalize(notation, contract) == "MY"

    def test_matches_mexico_accented(self) -> None:
        """Accented México resolves to MX."""
        contract = CountryContract(include_localized=True)
        notation = CountryNotation(shape="name", value="México")
        assert self.rule.matches(notation, contract) is True
        assert self.rule.normalize(notation, contract) == "MX"

    def test_matches_mexico_normalized(self) -> None:
        """ASCII/case-normalized MEXICO resolves to MX via normalization."""
        contract = CountryContract(include_localized=True)
        notation = CountryNotation(shape="name", value="MEXICO")
        assert self.rule.matches(notation, contract) is True
        assert self.rule.normalize(notation, contract) == "MX"

    def test_provenance_attributes(self) -> None:
        """Verify authority, spec name, year, lifecycle."""
        assert self.rule.provenance.authority == "Unicode"
        assert self.rule.provenance.specification_name == "CLDR v45"
        assert self.rule.provenance.publication_year == 2024
        assert self.rule.provenance.lifecycle == "active"

    def test_rule_name(self) -> None:
        """Verify name follows convention."""
        assert self.rule.name == "Section-localized-names"

    def test_strategy(self) -> None:
        """Verify the rule strategy enum."""
        assert self.rule.strategy == RuleStrategy.LOOKUP_TABLE
