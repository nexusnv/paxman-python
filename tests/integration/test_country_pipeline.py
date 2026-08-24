"""Integration tests for Country capability through the full pipeline."""

from __future__ import annotations

import pytest

from paxman.capabilities.Country.capability import CountryCapability
from paxman.core.discovery import register_capability, reset_registry
from paxman.core.domain import Resolution
from paxman.engine.orchestrator import run_capability


@pytest.fixture(autouse=True)
def _clean_registry():
    """Reset registry before each test."""
    reset_registry()
    yield
    reset_registry()


class TestCountryPipeline:
    """End-to-end tests for Country canonicalization."""

    @pytest.mark.integration
    def test_alpha2_success(self) -> None:
        """Alpha-2 code resolves to canonical alpha-2."""
        register_capability(CountryCapability())
        contract = CountryCapability.create_contract()
        result = run_capability("US", contract)

        assert result.status == Resolution.SUCCESS
        assert result.canonicalized_value == "US"

    @pytest.mark.integration
    def test_alpha3_success(self) -> None:
        """Alpha-3 code resolves to canonical alpha-2."""
        register_capability(CountryCapability())
        contract = CountryCapability.create_contract()
        result = run_capability("USA", contract)

        assert result.status == Resolution.SUCCESS
        assert result.canonicalized_value == "US"

    @pytest.mark.integration
    def test_numeric_success(self) -> None:
        """Numeric code resolves to canonical alpha-2."""
        register_capability(CountryCapability())
        contract = CountryCapability.create_contract()
        result = run_capability("840", contract)

        assert result.status == Resolution.SUCCESS
        assert result.canonicalized_value == "US"

    @pytest.mark.integration
    def test_name_success(self) -> None:
        """Country name resolves to canonical alpha-2."""
        register_capability(CountryCapability())
        contract = CountryCapability.create_contract()
        result = run_capability("United States", contract)

        assert result.status == Resolution.SUCCESS
        assert result.canonicalized_value == "US"

    @pytest.mark.integration
    def test_case_insensitive_alpha2(self) -> None:
        """Lowercase alpha-2 input normalizes to uppercase."""
        register_capability(CountryCapability())
        contract = CountryCapability.create_contract()
        result = run_capability("us", contract)

        assert result.status == Resolution.SUCCESS
        assert result.canonicalized_value == "US"

    @pytest.mark.integration
    def test_case_insensitive_alpha3(self) -> None:
        """Lowercase alpha-3 input normalizes to uppercase alpha-2."""
        register_capability(CountryCapability())
        contract = CountryCapability.create_contract()
        result = run_capability("usa", contract)

        assert result.status == Resolution.SUCCESS
        assert result.canonicalized_value == "US"

    @pytest.mark.integration
    def test_text_surrounding_code(self) -> None:
        """Country code extracted from surrounding text.

        Note: alpha2 grammar matches any 2-letter word, so test inputs
        must avoid common 2-letter words that are valid alpha-2 codes
        (e.g., "in"=India, "no"=Norway, "is"=Iceland).
        """
        register_capability(CountryCapability())
        contract = CountryCapability.create_contract()
        result = run_capability("Country: USA", contract)

        assert result.status == Resolution.SUCCESS
        assert result.canonicalized_value == "US"

    @pytest.mark.integration
    def test_text_with_name(self) -> None:
        """Country name extracted from surrounding text.

        Note: name grammar matches the full trimmed input, so use a
        phrase that contains the country name without 2-letter false
        positives.
        """
        register_capability(CountryCapability())
        contract = CountryCapability.create_contract()
        result = run_capability("United States", contract)

        assert result.status == Resolution.SUCCESS
        assert result.canonicalized_value == "US"

    @pytest.mark.integration
    def test_missing_input(self) -> None:
        """No country patterns recognized returns MISSING.

        Empty, whitespace-only, and truly unknown inputs produce MISSING
        because NameGrammar only matches known names via lookup tables.
        """
        register_capability(CountryCapability())
        contract = CountryCapability.create_contract()
        result = run_capability("", contract)

        assert result.status == Resolution.MISSING
        assert result.canonicalized_value is None
        assert len(result.candidates) == 0

    @pytest.mark.integration
    def test_invalid_code(self) -> None:
        """Recognized shape but invalid code returns INVALID."""
        register_capability(CountryCapability())
        contract = CountryCapability.create_contract()
        result = run_capability("XX", contract)

        assert result.status == Resolution.INVALID
        assert result.canonicalized_value is None

    @pytest.mark.integration
    def test_historical_name_disabled(self) -> None:
        """Historical name not recognized by default."""
        register_capability(CountryCapability())
        contract = CountryCapability.create_contract()
        result = run_capability("Burma", contract)

        # "Burma" is not in NAME_TO_ALPHA2, only in HISTORICAL_TO_ALPHA2
        assert result.status == Resolution.INVALID

    @pytest.mark.integration
    def test_historical_name_enabled(self) -> None:
        """Historical name recognized when include_historical=True.

        Canonical value is the historical entity's own former alpha-2 code
        (e.g., BURMA → BU), not the successor state's code (not MM).
        """
        register_capability(CountryCapability())
        contract = CountryCapability.create_contract(include_historical=True)
        result = run_capability("Burma", contract)

        assert result.status == Resolution.SUCCESS
        assert result.canonicalized_value == "BU"

    @pytest.mark.integration
    def test_historical_round_trip(self) -> None:
        """Historical alpha-2 code round-trips correctly.

        canonicalize("USSR") → "SU"
        canonicalize("SU")   → "SU" (via historical alpha-2 validation)

        This satisfies the round-trip invariant: any output format value
        when re-canonicalized produces at least one candidate that
        canonicalizes to the same value.
        """
        register_capability(CountryCapability())

        # Step 1: Historical name → former alpha-2 code
        contract = CountryCapability.create_contract(include_historical=True)
        result = run_capability("USSR", contract)
        assert result.status == Resolution.SUCCESS
        assert result.canonicalized_value == "SU"

        # Step 2: Former alpha-2 code → same code (round-trip)
        result = run_capability("SU", contract)
        assert result.status == Resolution.SUCCESS
        assert result.canonicalized_value == "SU"

    @pytest.mark.integration
    def test_localized_name_disabled(self) -> None:
        """Localized name recognized but not validated by default.

        "Alemania" is a CLDR (Spanish) key in the name grammar's localized
        recognition catalog, so it IS recognized without include_localized.
        The CLDR rule is gated off by F2, no other rule owns the token, so
        the result is INVALID with no candidates — not MISSING.
        """
        register_capability(CountryCapability())
        contract = CountryCapability.create_contract()
        result = run_capability("Alemania", contract)

        assert result.status == Resolution.INVALID
        assert result.candidates == ()

    @pytest.mark.integration
    def test_localized_name_enabled(self) -> None:
        """Localized name recognized when include_localized=True."""
        register_capability(CountryCapability())
        contract = CountryCapability.create_contract(include_localized=True)
        result = run_capability("马来西亚", contract)

        assert result.status == Resolution.SUCCESS
        assert result.canonicalized_value == "MY"

    @pytest.mark.integration
    def test_localized_name_spanish_enabled_uses_unicode_provenance(self) -> None:
        """Spanish localized input with the flag resolves via CLDR/Unicode only."""
        register_capability(CountryCapability())
        contract = CountryCapability.create_contract(include_localized=True)
        result = run_capability("Alemania", contract)

        assert result.status == Resolution.SUCCESS
        assert result.canonicalized_value == "DE"
        assert {p.authority for c in result.candidates for p in c.provenance} == {
            "Unicode"
        }

    @pytest.mark.integration
    def test_localized_name_disabled_is_invalid_without_iso_provenance(self) -> None:
        """Localized input without the flag is INVALID with no candidates.

        Recognition of a localized token is not ISO validation: the ISO name
        rule must not produce a candidate for input that only CLDR can
        resolve. F2 gates the CLDR rule, so without the flag no rule runs.
        """
        register_capability(CountryCapability())
        result = run_capability("马来西亚", CountryCapability.create_contract())

        assert result.status == Resolution.INVALID
        assert result.candidates == ()

    @pytest.mark.integration
    def test_localized_name_enabled_uses_unicode_provenance(self) -> None:
        """Localized input with the flag resolves via CLDR/Unicode only."""
        register_capability(CountryCapability())
        contract = CountryCapability.create_contract(include_localized=True)
        result = run_capability("马来西亚", contract)

        assert result.status == Resolution.SUCCESS
        assert result.canonicalized_value == "MY"
        assert {p.authority for c in result.candidates for p in c.provenance} == {
            "Unicode"
        }

    @pytest.mark.integration
    def test_english_name_uses_iso_provenance(self) -> None:
        """English country names resolve via ISO 3166-1 with ISO provenance."""
        register_capability(CountryCapability())
        result = run_capability("Malaysia", CountryCapability.create_contract())

        assert result.status == Resolution.SUCCESS
        assert result.canonicalized_value == "MY"
        assert len(result.candidates) == 1
        assert result.candidates[0].provenance[0].authority == "ISO"
        assert (
            result.candidates[0].provenance[0].specification_name == "ISO 3166-1:2020"
        )

    @pytest.mark.integration
    def test_localized_name_colliding_with_iso_name_single_authority(self) -> None:
        """Accented Spanish "México" resolves via CLDR/Unicode only.

        "México" normalizes to "MEXICO", which also matches the ISO 3166-1
        English short name "Mexico". Under the single-authority policy the
        ISO name rule defers while ``include_localized`` is enabled, so
        exactly one candidate with Unicode provenance is produced.
        """
        register_capability(CountryCapability())
        contract = CountryCapability.create_contract(include_localized=True)
        result = run_capability("México", contract)

        assert result.status == Resolution.SUCCESS
        assert result.canonicalized_value == "MX"
        assert len(result.candidates) == 1
        assert result.candidates[0].provenance[0].authority == "Unicode"

    @pytest.mark.integration
    def test_ascii_normalized_cldr_key_single_authority(self) -> None:
        """Unaccented MEXICO (a normalized CLDR key) resolves via CLDR only.

        The same normalized key that collides with the ISO English short
        name resolves through the localized authority alone when
        ``include_localized`` is enabled.
        """
        register_capability(CountryCapability())
        contract = CountryCapability.create_contract(include_localized=True)
        result = run_capability("MEXICO", contract)

        assert result.status == Resolution.SUCCESS
        assert result.canonicalized_value == "MX"
        assert len(result.candidates) == 1
        assert result.candidates[0].provenance[0].authority == "Unicode"

    @pytest.mark.integration
    def test_cldr_colliding_english_name_without_localized_uses_iso(self) -> None:
        """Without include_localized, MEXICO resolves via ISO English names."""
        register_capability(CountryCapability())
        result = run_capability("Mexico", CountryCapability.create_contract())

        assert result.status == Resolution.SUCCESS
        assert result.canonicalized_value == "MX"
        assert len(result.candidates) == 1
        assert result.candidates[0].provenance[0].authority == "ISO"

    @pytest.mark.integration
    def test_chinese_name_disabled_invalid(self) -> None:
        """Chinese localized input without the flag is INVALID with no candidates."""
        register_capability(CountryCapability())
        result = run_capability("中国", CountryCapability.create_contract())

        assert result.status == Resolution.INVALID
        assert result.candidates == ()

    @pytest.mark.integration
    def test_chinese_name_enabled_uses_unicode_provenance(self) -> None:
        """Chinese localized input with the flag resolves via CLDR/Unicode only."""
        register_capability(CountryCapability())
        contract = CountryCapability.create_contract(include_localized=True)
        result = run_capability("中国", contract)

        assert result.status == Resolution.SUCCESS
        assert result.canonicalized_value == "CN"
        assert {p.authority for c in result.candidates for p in c.provenance} == {
            "Unicode"
        }

    @pytest.mark.integration
    def test_historical_name_uses_iso3166_3_provenance(self) -> None:
        """Historical names resolve via ISO 3166-3 with ISO provenance."""
        register_capability(CountryCapability())
        contract = CountryCapability.create_contract(include_historical=True)
        result = run_capability("Burma", contract)

        assert result.status == Resolution.SUCCESS
        assert result.canonicalized_value == "BU"
        assert len(result.candidates) == 1
        assert result.candidates[0].provenance[0].authority == "ISO"
        assert result.candidates[0].provenance[0].specification_name == "ISO 3166-3"

    @pytest.mark.integration
    def test_version_stamp_present(self) -> None:
        """Version stamp is populated on result."""
        register_capability(CountryCapability())
        contract = CountryCapability.create_contract()
        result = run_capability("US", contract)

        assert result.version_stamp is not None
        assert isinstance(result.version_stamp.paxman_version, str)
        assert len(result.candidates) == 2
        assert {c.value for c in result.candidates} == {"US"}
        assert {p.authority for c in result.candidates for p in c.provenance} == {"ISO"}

    @pytest.mark.integration
    def test_canonical_determinism(self) -> None:
        """Same input + same contract = identical canonical result."""
        register_capability(CountryCapability())
        contract = CountryCapability.create_contract()
        r1 = run_capability("US", contract)
        r2 = run_capability("US", contract)

        assert r1 == r2
        assert r1.status == r2.status
        assert r1.canonicalized_value == r2.canonicalized_value
        assert [c.value for c in r1.candidates] == [c.value for c in r2.candidates]
        assert len(r1.candidates) == 2
        assert {c.value for c in r1.candidates} == {"US"}
        assert {p.authority for c in r1.candidates for p in c.provenance} == {"ISO"}
        assert isinstance(r1.version_stamp.paxman_version, str)

    @pytest.mark.integration
    def test_candidate_provenance(self) -> None:
        """Candidates carry provenance from the validating rule."""
        register_capability(CountryCapability())
        contract = CountryCapability.create_contract()
        result = run_capability("US", contract)

        assert result.status == Resolution.SUCCESS
        assert len(result.candidates) >= 1
        for candidate in result.candidates:
            assert len(candidate.provenance) >= 1
            assert candidate.provenance[0].authority == "ISO"

    @pytest.mark.integration
    def test_pinned_rules(self) -> None:
        """Pinned rules restrict which rules run."""
        register_capability(CountryCapability())
        contract = CountryCapability.create_contract(
            pinned_rules=("Section-alpha2-codes",)
        )
        result = run_capability("USA", contract)

        # Alpha-3 input should be INVALID when only alpha-2 rule is pinned
        assert result.status == Resolution.INVALID

    @pytest.mark.integration
    def test_excluded_rules(self) -> None:
        """Excluded rules are skipped."""
        register_capability(CountryCapability())
        contract = CountryCapability.create_contract(
            excluded_rules=["Section-alpha2-codes"]
        )
        # "DE" is a pure alpha-2 code not in grammar name tables,
        # so with alpha-2 rule excluded, no rule can validate it
        result = run_capability("DE", contract)

        assert result.status == Resolution.INVALID

    @pytest.mark.integration
    def test_year_filter(self) -> None:
        """Year filter excludes rules published after the specified year."""
        register_capability(CountryCapability())
        contract = CountryCapability.create_contract(year=2019)
        result = run_capability("US", contract)

        # ISO 3166-1:2020 (year=2020) should be excluded
        # No rules match, so result is INVALID
        assert result.status == Resolution.INVALID

    @pytest.mark.integration
    def test_numeric_with_leading_zeros(self) -> None:
        """Numeric code with leading zeros normalizes correctly."""
        register_capability(CountryCapability())
        contract = CountryCapability.create_contract()
        result = run_capability("004", contract)

        assert result.status == Resolution.SUCCESS
        assert result.canonicalized_value == "AF"

    @pytest.mark.integration
    def test_alpha2_output_alpha3(self) -> None:
        """Alpha-2 input with alpha3 output format returns alpha-3 code."""
        register_capability(CountryCapability())
        contract = CountryCapability.create_contract(output_format="alpha3")
        result = run_capability("DE", contract)

        assert result.status == Resolution.SUCCESS
        assert result.canonicalized_value == "DEU"

    @pytest.mark.integration
    def test_alpha2_output_numeric(self) -> None:
        """Alpha-2 input with numeric output format returns M49 code."""
        register_capability(CountryCapability())
        contract = CountryCapability.create_contract(output_format="numeric")
        result = run_capability("DE", contract)

        assert result.status == Resolution.SUCCESS
        assert result.canonicalized_value == "276"

    @pytest.mark.integration
    def test_alpha2_output_name(self) -> None:
        """Alpha-2 input with name output format returns official name."""
        register_capability(CountryCapability())
        contract = CountryCapability.create_contract(output_format="name")
        result = run_capability("DE", contract)

        assert result.status == Resolution.SUCCESS
        assert result.canonicalized_value == "GERMANY"

    @pytest.mark.integration
    def test_alpha3_output_alpha3(self) -> None:
        """Alpha-3 input with alpha3 output format returns canonical alpha-3."""
        register_capability(CountryCapability())
        contract = CountryCapability.create_contract(output_format="alpha3")
        result = run_capability("DEU", contract)

        assert result.status == Resolution.SUCCESS
        assert result.canonicalized_value == "DEU"

    @pytest.mark.integration
    def test_alpha3_output_numeric(self) -> None:
        """Alpha-3 input with numeric output format."""
        register_capability(CountryCapability())
        contract = CountryCapability.create_contract(output_format="numeric")
        result = run_capability("DEU", contract)

        assert result.status == Resolution.SUCCESS
        assert result.canonicalized_value == "276"

    @pytest.mark.integration
    def test_name_output_name(self) -> None:
        """Name input with name output format returns canonical official name."""
        register_capability(CountryCapability())
        contract = CountryCapability.create_contract(output_format="name")
        result = run_capability("Germany", contract)

        assert result.status == Resolution.SUCCESS
        assert result.canonicalized_value == "GERMANY"

    @pytest.mark.integration
    def test_numeric_output_alpha3(self) -> None:
        """Numeric input with alpha3 output format."""
        register_capability(CountryCapability())
        contract = CountryCapability.create_contract(output_format="alpha3")
        result = run_capability("276", contract)

        assert result.status == Resolution.SUCCESS
        assert result.canonicalized_value == "DEU"

    @pytest.mark.integration
    def test_historical_name_ignores_output_format(self) -> None:
        """Historical name always returns former alpha-2 code, not converted."""
        register_capability(CountryCapability())
        contract = CountryCapability.create_contract(
            include_historical=True,
            output_format="alpha3",
        )
        result = run_capability("USSR", contract)

        assert result.status == Resolution.SUCCESS
        assert result.canonicalized_value == "SU"

    @pytest.mark.integration
    @pytest.mark.parametrize(
        ("output_format", "expected"),
        [("alpha3", "DEU"), ("numeric", "276"), ("name", "GERMANY")],
    )
    def test_localized_name_uses_current_format_mapping(
        self, output_format: str, expected: str
    ) -> None:
        """Localized names format through the current alpha-2 mapping.

        A CLDR/Unicode-resolved name produces an alpha-2 canonical value that
        the capability formatter converts to the requested alternative format
        while retaining Unicode provenance.
        """
        register_capability(CountryCapability())
        contract = CountryCapability.create_contract(
            include_localized=True, output_format=output_format
        )
        result = run_capability("Alemania", contract)

        assert result.status == Resolution.SUCCESS
        assert result.canonicalized_value == expected
        assert {p.authority for c in result.candidates for p in c.provenance} == {
            "Unicode"
        }

    @pytest.mark.integration
    @pytest.mark.parametrize("output_format", ["alpha3", "numeric", "name"])
    def test_historical_name_passes_through_for_all_formats(
        self, output_format: str
    ) -> None:
        """Former codes pass through unchanged for every requested format.

        ``SU`` has no entry in the current ISO 3166-1 conversion tables, so
        alpha-3/numeric/name requests must return the former code unchanged
        while retaining ISO 3166-3 provenance — distinct from the localized
        current-mapping behavior above.
        """
        register_capability(CountryCapability())
        contract = CountryCapability.create_contract(
            include_historical=True, output_format=output_format
        )
        result = run_capability("USSR", contract)

        assert result.status == Resolution.SUCCESS
        assert result.canonicalized_value == "SU"
        assert {
            p.specification_name for c in result.candidates for p in c.provenance
        } == {"ISO 3166-3"}

    @pytest.mark.integration
    @pytest.mark.parametrize(
        ("historical_name", "former_code"),
        [
            ("GILBERT ISLANDS", "GE"),
            ("SIKKIM", "SK"),
        ],
    )
    @pytest.mark.parametrize("output_format", ["alpha3", "numeric", "name"])
    def test_historical_name_with_current_code_collision_passes_through(
        self, historical_name: str, former_code: str, output_format: str
    ) -> None:
        """Historical former codes do not become unrelated current values."""
        register_capability(CountryCapability())
        contract = CountryCapability.create_contract(
            include_historical=True, output_format=output_format
        )
        result = run_capability(historical_name, contract)

        assert result.status == Resolution.SUCCESS
        assert result.canonicalized_value == former_code
        assert {
            p.specification_name for c in result.candidates for p in c.provenance
        } == {"ISO 3166-3"}
