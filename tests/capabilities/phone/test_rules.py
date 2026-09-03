"""Tests for Phone validation rules."""

from paxman.capabilities.Phone.contract import PhoneContract
from paxman.capabilities.Phone.notation import PhoneNotation
from paxman.capabilities.Phone.rules.e164_ed2010 import (
    Section6_1InternationalNumber,
    Section6_2CountryCode,
)
from paxman.capabilities.Phone.rules.nanp_ed2024 import (
    Section1_1NANPStructure,
    Section1_2ServiceNPA,
)
from paxman.capabilities.Phone.rules.rfc_3966_ed2004 import Section3TelUri
from paxman.core.domain import RuleStrategy


class TestSection6_1InternationalNumber:
    """Tests for Section6_1InternationalNumber rule."""

    def setup_method(self) -> None:
        self.rule = Section6_1InternationalNumber()
        self.contract = PhoneContract()

    def test_matches_valid_e164(self) -> None:
        """Happy path: valid E.164 number."""
        notation = PhoneNotation(shape="e164", value="15551234567")
        assert self.rule.matches(notation, self.contract) is True

    def test_matches_uk_number(self) -> None:
        """Edge case: 2-digit country code."""
        notation = PhoneNotation(shape="e164", value="442079460958")
        assert self.rule.matches(notation, self.contract) is True

    def test_matches_three_digit_cc(self) -> None:
        """Edge case: 3-digit country code (Taiwan 886)."""
        notation = PhoneNotation(shape="e164", value="886212345678")
        assert self.rule.matches(notation, self.contract) is True

    def test_longest_prefix_rule_emits_default_e164(self) -> None:
        """Rules emit the default E.164 form regardless of output_format."""
        notation = PhoneNotation(shape="e164", value="886212345678")
        contract = PhoneContract(output_format="national", default_country="US")
        assert self.rule.normalize(notation, contract) == "+886212345678"

    def test_matches_max_length(self) -> None:
        """Edge case: exactly 15 digits."""
        notation = PhoneNotation(shape="e164", value="123456789012345")
        assert self.rule.matches(notation, self.contract) is True

    def test_rejects_too_long(self) -> None:
        """16+ digits exceeds E.164 maximum."""
        notation = PhoneNotation(shape="e164", value="1234567890123456")
        assert self.rule.matches(notation, self.contract) is False

    def test_rejects_bare_country_code(self) -> None:
        """A bare country code (no NSN) is not a valid E.164 number."""
        notation = PhoneNotation(shape="e164", value="1")
        assert self.rule.matches(notation, self.contract) is False

    def test_rejects_one_digit_nsn(self) -> None:
        """A 1-digit NSN (e.g., '+12' → CC 1 + NSN '2') is degenerate."""
        notation = PhoneNotation(shape="e164", value="12")
        assert self.rule.matches(notation, self.contract) is False

    def test_rejects_bare_two_digit_cc(self) -> None:
        """A 2-digit country code with no NSN is not valid either."""
        notation = PhoneNotation(shape="e164", value="44")
        assert self.rule.matches(notation, self.contract) is False

    def test_rejects_unassigned_cc(self) -> None:
        """999 is not an assigned country code."""
        notation = PhoneNotation(shape="e164", value="999123456789")
        assert self.rule.matches(notation, self.contract) is False

    def test_rejects_wrong_shape(self) -> None:
        """Notation with wrong shape."""
        notation = PhoneNotation(shape="national", value="15551234567")
        assert self.rule.matches(notation, self.contract) is False

    def test_rejects_non_digits(self) -> None:
        """Value containing non-digits."""
        notation = PhoneNotation(shape="e164", value="1555a1234567")
        assert self.rule.matches(notation, self.contract) is False

    def test_normalize_produces_canonical(self) -> None:
        """Verify exact canonical output."""
        notation = PhoneNotation(shape="e164", value="15551234567")
        assert self.rule.normalize(notation, self.contract) == "+15551234567"

    def test_normalize_ignores_rfc3966_contract_format(self) -> None:
        """Rules emit default E.164 even under an rfc3966 contract."""
        notation = PhoneNotation(shape="e164", value="15551234567")
        contract = PhoneContract(output_format="rfc3966")
        assert self.rule.normalize(notation, contract) == "+15551234567"

    def test_normalize_ignores_national_contract_format(self) -> None:
        """Rules emit default E.164 even under a national contract."""
        notation = PhoneNotation(shape="e164", value="15551234567")
        contract = PhoneContract(output_format="national", default_country="US")
        assert self.rule.normalize(notation, contract) == "+15551234567"

    def test_provenance_attributes(self) -> None:
        """Verify authority, spec name, year, lifecycle."""
        assert self.rule.provenance.authority == "ITU-T"
        assert self.rule.provenance.specification_name == "E.164"
        assert self.rule.provenance.publication_year == 2010
        assert self.rule.provenance.lifecycle == "active"

    def test_rule_name(self) -> None:
        """Verify name follows convention."""
        assert self.rule.name == "Section 6.1-international-number"

    def test_strategy(self) -> None:
        """Verify the rule strategy enum."""
        assert self.rule.strategy == RuleStrategy.PARSER

    def test_citation(self) -> None:
        """Verify citation is set."""
        assert "6.1" in self.rule.citation


class TestSection6_2CountryCode:
    """Tests for Section6_2CountryCode rule."""

    def setup_method(self) -> None:
        self.rule = Section6_2CountryCode()
        self.contract = PhoneContract()

    def test_matches_assigned_cc(self) -> None:
        """Happy path: assigned country code."""
        notation = PhoneNotation(shape="e164", value="442079460958")
        assert self.rule.matches(notation, self.contract) is True

    def test_matches_single_digit_cc(self) -> None:
        """Edge case: NANP country code 1."""
        notation = PhoneNotation(shape="e164", value="15551234567")
        assert self.rule.matches(notation, self.contract) is True

    def test_matches_three_digit_cc(self) -> None:
        """Edge case: 3-digit country code."""
        notation = PhoneNotation(shape="e164", value="886212345678")
        assert self.rule.matches(notation, self.contract) is True

    def test_rejects_unassigned_cc(self) -> None:
        """Unassigned country code."""
        notation = PhoneNotation(shape="e164", value="999123456789")
        assert self.rule.matches(notation, self.contract) is False

    def test_rejects_non_digits(self) -> None:
        """Value containing non-digits."""
        notation = PhoneNotation(shape="e164", value="1555a1234567")
        assert self.rule.matches(notation, self.contract) is False

    def test_rejects_too_long(self) -> None:
        """16+ digits exceeds E.164 maximum (shared structural predicate)."""
        notation = PhoneNotation(shape="e164", value="1234567890123456")
        assert self.rule.matches(notation, self.contract) is False

    def test_rejects_wrong_shape(self) -> None:
        """Notation with wrong shape."""
        notation = PhoneNotation(shape="national", value="15551234567")
        assert self.rule.matches(notation, self.contract) is False

    def test_normalize_produces_canonical(self) -> None:
        """Verify exact canonical output."""
        notation = PhoneNotation(shape="e164", value="15551234567")
        assert self.rule.normalize(notation, self.contract) == "+15551234567"

    def test_provenance_attributes(self) -> None:
        """Verify authority, spec name, year, lifecycle."""
        assert self.rule.provenance.authority == "ITU-T"
        assert self.rule.provenance.specification_name == "E.164"
        assert self.rule.provenance.publication_year == 2010

    def test_rule_name(self) -> None:
        """Verify name follows convention."""
        assert self.rule.name == "Section 6.2-country-code"

    def test_strategy(self) -> None:
        """Verify the rule strategy enum."""
        assert self.rule.strategy == RuleStrategy.LOOKUP_TABLE

    def test_citation(self) -> None:
        """Verify citation is set."""
        assert "country code" in self.rule.citation.lower()


class TestSection3TelUri:
    """Tests for Section3TelUri rule."""

    def setup_method(self) -> None:
        self.rule = Section3TelUri()
        self.contract = PhoneContract()

    def test_matches_valid_global_number(self) -> None:
        """Happy path: valid tel: URI global number."""
        notation = PhoneNotation(shape="rfc3966", value="15551234567")
        assert self.rule.matches(notation, self.contract) is True

    def test_matches_with_extension(self) -> None:
        """Edge case: extension present."""
        notation = PhoneNotation(shape="rfc3966", value="15551234567", extension="890")
        assert self.rule.matches(notation, self.contract) is True

    def test_rejects_unassigned_cc(self) -> None:
        """Unassigned country code in URI."""
        notation = PhoneNotation(shape="rfc3966", value="999123456789")
        assert self.rule.matches(notation, self.contract) is False

    def test_rejects_too_long(self) -> None:
        """16+ digits exceeds E.164 maximum."""
        notation = PhoneNotation(shape="rfc3966", value="1234567890123456")
        assert self.rule.matches(notation, self.contract) is False

    def test_rejects_one_digit_nsn(self) -> None:
        """A 1-digit NSN is degenerate (shared E.164 structural check)."""
        notation = PhoneNotation(shape="rfc3966", value="12")
        assert self.rule.matches(notation, self.contract) is False

    def test_rejects_non_digits(self) -> None:
        """Value containing non-digits."""
        notation = PhoneNotation(shape="rfc3966", value="1555a1234567")
        assert self.rule.matches(notation, self.contract) is False

    def test_rejects_wrong_shape(self) -> None:
        """Notation with wrong shape."""
        notation = PhoneNotation(shape="e164", value="15551234567")
        assert self.rule.matches(notation, self.contract) is False

    def test_normalize_produces_canonical(self) -> None:
        """Verify exact canonical output (default e164)."""
        notation = PhoneNotation(shape="rfc3966", value="15551234567")
        assert self.rule.normalize(notation, self.contract) == "+15551234567"

    def test_normalize_ignores_rfc3966_contract_format(self) -> None:
        """Rules emit default E.164 even under an rfc3966 contract."""
        notation = PhoneNotation(shape="rfc3966", value="15551234567")
        contract = PhoneContract(output_format="rfc3966")
        assert self.rule.normalize(notation, contract) == "+15551234567"

    def test_normalize_ignores_extension_for_rfc3966_contract(self) -> None:
        """Rules do not render extensions; that is the capability seam."""
        notation = PhoneNotation(shape="rfc3966", value="15551234567", extension="890")
        contract = PhoneContract(output_format="rfc3966")
        assert self.rule.normalize(notation, contract) == "+15551234567"

    def test_normalize_ignores_national_contract_format(self) -> None:
        """Rules emit default E.164 even under a national contract."""
        notation = PhoneNotation(shape="rfc3966", value="15551234567")
        contract = PhoneContract(output_format="national", default_country="US")
        assert self.rule.normalize(notation, contract) == "+15551234567"

    def test_provenance_attributes(self) -> None:
        """Verify authority, spec name, year, lifecycle."""
        assert self.rule.provenance.authority == "IETF"
        assert self.rule.provenance.specification_name == "RFC 3966"
        assert self.rule.provenance.publication_year == 2004
        assert self.rule.provenance.lifecycle == "active"

    def test_rule_name(self) -> None:
        """Verify name follows convention."""
        assert self.rule.name == "Section 3-tel-uri"

    def test_strategy(self) -> None:
        """Verify the rule strategy enum."""
        assert self.rule.strategy == RuleStrategy.PARSER

    def test_citation(self) -> None:
        """Verify citation identifies the RFC 3966 tel-URI rule."""
        assert "tel URI" in self.rule.citation


class TestSection1_1NANPStructure:
    """Tests for Section1_1NANPStructure rule."""

    def setup_method(self) -> None:
        self.rule = Section1_1NANPStructure()
        self.contract = PhoneContract(default_country="US")

    def test_matches_valid_national(self) -> None:
        """Happy path: valid NANP number (NXX first digit 2-9)."""
        notation = PhoneNotation(shape="national", value="5552345678")
        assert self.rule.matches(notation, self.contract) is True

    def test_matches_with_trunk(self) -> None:
        """Edge case: leading trunk 1."""
        notation = PhoneNotation(shape="national", value="15552345678")
        assert self.rule.matches(notation, self.contract) is True

    def test_matches_toll_free(self) -> None:
        """Edge case: toll-free NPA."""
        notation = PhoneNotation(shape="national", value="8005551234")
        assert self.rule.matches(notation, self.contract) is True

    def test_rejects_n11_npa(self) -> None:
        """911 is not an assignable NPA."""
        notation = PhoneNotation(shape="national", value="9115551234")
        assert self.rule.matches(notation, self.contract) is False

    def test_rejects_n11_nxx(self) -> None:
        """411 is not an assignable NXX."""
        notation = PhoneNotation(shape="national", value="5554111234")
        assert self.rule.matches(notation, self.contract) is False

    def test_rejects_fictional_555_range(self) -> None:
        """555-0100..555-0199 (NXX=555, line 01xx) is reserved for fiction."""
        notation = PhoneNotation(shape="national", value="5555550100")
        assert self.rule.matches(notation, self.contract) is False

    def test_rejects_fictional_555_upper_bound(self) -> None:
        """Upper edge of the fictional range is still reserved."""
        notation = PhoneNotation(shape="national", value="15555550199")
        assert self.rule.matches(notation, self.contract) is False

    def test_accepts_555_outside_fictional_range(self) -> None:
        """555 NXX with a line number outside 0100-0199 is structurally valid."""
        notation = PhoneNotation(shape="national", value="5555550200")
        assert self.rule.matches(notation, self.contract) is True

    def test_rejects_npa_starting_with_0(self) -> None:
        """NPA first digit must be 2-9."""
        notation = PhoneNotation(shape="national", value="05551234567")
        assert self.rule.matches(notation, self.contract) is False

    def test_rejects_nxx_starting_with_1(self) -> None:
        """NXX first digit must be 2-9 (123 is not an assignable exchange)."""
        notation = PhoneNotation(shape="national", value="5551234567")
        assert self.rule.matches(notation, self.contract) is False

    def test_rejects_too_short(self) -> None:
        """9 digits is not a full NANP number."""
        notation = PhoneNotation(shape="national", value="555123456")
        assert self.rule.matches(notation, self.contract) is False

    def test_rejects_too_long(self) -> None:
        """12 digits is not a full NANP number."""
        notation = PhoneNotation(shape="national", value="155551234567")
        assert self.rule.matches(notation, self.contract) is False

    def test_rejects_wrong_shape(self) -> None:
        """Notation with wrong shape."""
        notation = PhoneNotation(shape="e164", value="15551234567")
        assert self.rule.matches(notation, self.contract) is False

    def test_rejects_without_default_country(self) -> None:
        """National numbers need default_country."""
        notation = PhoneNotation(shape="national", value="5552345678")
        contract = PhoneContract()
        assert self.rule.matches(notation, contract) is False

    def test_rejects_non_us_default_country(self) -> None:
        """default_country outside NANP does not match (Milestone 1: US only)."""
        notation = PhoneNotation(shape="national", value="5552345678")
        contract = PhoneContract(default_country="GB")
        assert self.rule.matches(notation, contract) is False

    def test_normalize_produces_canonical(self) -> None:
        """Verify exact canonical output."""
        notation = PhoneNotation(shape="national", value="5552345678")
        assert self.rule.normalize(notation, self.contract) == "+15552345678"

    def test_normalize_strips_trunk(self) -> None:
        """Trunk 1 is not duplicated in canonical output."""
        notation = PhoneNotation(shape="national", value="15552345678")
        assert self.rule.normalize(notation, self.contract) == "+15552345678"

    def test_normalize_defensive_invalid_structure(self) -> None:
        """Normalize is defensive when the structure check fails."""
        notation = PhoneNotation(shape="national", value="800555123")
        assert self.rule.normalize(notation, self.contract) == "800555123"

    def test_normalize_national_format_is_default_e164(self) -> None:
        """Rules emit default E.164 even under a national contract."""
        notation = PhoneNotation(shape="national", value="5552345678")
        contract = PhoneContract(output_format="national", default_country="US")
        assert self.rule.normalize(notation, contract) == "+15552345678"

    def test_normalize_ignores_rfc3966_contract_format(self) -> None:
        """Rules emit default E.164 even under an rfc3966 contract."""
        notation = PhoneNotation(shape="national", value="5552345678")
        contract = PhoneContract(default_country="US", output_format="rfc3966")
        assert self.rule.normalize(notation, contract) == "+15552345678"

    def test_provenance_attributes(self) -> None:
        """Verify authority, spec name, year, lifecycle."""
        assert self.rule.provenance.authority == "NANPA"
        assert self.rule.provenance.publication_year == 2024
        assert self.rule.provenance.lifecycle == "active"

    def test_rule_name(self) -> None:
        """Verify name follows convention."""
        assert self.rule.name == "Section 1.1-nanp-structure"

    def test_strategy(self) -> None:
        """Verify the rule strategy enum."""
        assert self.rule.strategy == RuleStrategy.REGEX

    def test_citation(self) -> None:
        """Verify citation is set."""
        assert "structure" in self.rule.citation.lower()


class TestSection1_2ServiceNPA:
    """Tests for Section1_2ServiceNPA rule."""

    def setup_method(self) -> None:
        self.rule = Section1_2ServiceNPA()
        self.contract = PhoneContract(default_country="US")

    def test_matches_toll_free(self) -> None:
        """Happy path: toll-free NPA."""
        notation = PhoneNotation(shape="national", value="8005551234")
        assert self.rule.matches(notation, self.contract) is True

    def test_matches_premium(self) -> None:
        """Edge case: premium rate 900."""
        notation = PhoneNotation(shape="national", value="9005551234")
        assert self.rule.matches(notation, self.contract) is True

    def test_matches_833(self) -> None:
        """Edge case: newer toll-free NPA."""
        notation = PhoneNotation(shape="national", value="8335551234")
        assert self.rule.matches(notation, self.contract) is True

    def test_rejects_geographic_npa(self) -> None:
        """Geographic NPA (212) is not a service code."""
        notation = PhoneNotation(shape="national", value="2125551234")
        assert self.rule.matches(notation, self.contract) is False

    def test_rejects_without_default_country(self) -> None:
        """Service NPAs still need default_country."""
        notation = PhoneNotation(shape="national", value="8005551234")
        contract = PhoneContract()
        assert self.rule.matches(notation, contract) is False

    def test_rejects_wrong_shape(self) -> None:
        """Notation with wrong shape."""
        notation = PhoneNotation(shape="e164", value="8005551234")
        assert self.rule.matches(notation, self.contract) is False

    def test_normalize_produces_canonical(self) -> None:
        """Verify exact canonical output."""
        notation = PhoneNotation(shape="national", value="8005551234")
        assert self.rule.normalize(notation, self.contract) == "+18005551234"

    def test_normalize_strips_trunk(self) -> None:
        """Trunk 1 is not duplicated in canonical output."""
        notation = PhoneNotation(shape="national", value="18005551234")
        assert self.rule.normalize(notation, self.contract) == "+18005551234"

    def test_normalize_ignores_rfc3966_contract_format(self) -> None:
        """Rules emit default E.164 even under an rfc3966 contract."""
        notation = PhoneNotation(shape="national", value="8005551234")
        contract = PhoneContract(default_country="US", output_format="rfc3966")
        assert self.rule.normalize(notation, contract) == "+18005551234"

    def test_rejects_structural_failure(self) -> None:
        """Non-NANP digits fail the structural check (digits is None branch)."""
        notation = PhoneNotation(shape="national", value="800555123")
        assert self.rule.matches(notation, self.contract) is False

    def test_normalize_defensive_invalid_structure(self) -> None:
        """Normalize is defensive when the structure check fails."""
        notation = PhoneNotation(shape="national", value="800555123")
        assert self.rule.normalize(notation, self.contract) == "800555123"

    def test_provenance_attributes(self) -> None:
        """Verify authority, spec name, year, lifecycle."""
        assert self.rule.provenance.authority == "NANPA"
        assert self.rule.provenance.publication_year == 2024

    def test_rule_name(self) -> None:
        """Verify name follows convention."""
        assert self.rule.name == "Section 1.2-service-npa"

    def test_strategy(self) -> None:
        """Verify the rule strategy enum."""
        assert self.rule.strategy == RuleStrategy.LOOKUP_TABLE

    def test_citation(self) -> None:
        """Verify citation is set."""
        assert "service" in self.rule.citation.lower()
