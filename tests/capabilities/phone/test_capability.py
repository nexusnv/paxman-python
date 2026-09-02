"""Tests for Phone capability."""

import pytest

from paxman.api import canonicalize
from paxman.capabilities.Phone.capability import PhoneCapability
from paxman.capabilities.Phone.contract import PhoneContract
from paxman.capabilities.Phone.notation import PhoneNotation
from paxman.core.capability import Capability
from paxman.core.discovery import register_capability, reset_registry
from paxman.core.domain import Resolution
from paxman.core.errors import ContractError


class TestPhoneNotation:
    """Tests for PhoneNotation dataclass."""

    def test_creates_with_fields(self) -> None:
        """Verify field access."""
        notation = PhoneNotation(shape="e164", value="15551234567")
        assert notation.shape == "e164"
        assert notation.value == "15551234567"
        assert notation.extension == ""

    def test_creates_with_extension(self) -> None:
        """Verify extension field."""
        notation = PhoneNotation(shape="rfc3966", value="15551234567", extension="890")
        assert notation.extension == "890"

    def test_is_frozen(self) -> None:
        """Verify immutability."""
        notation = PhoneNotation(shape="e164", value="15551234567")
        with pytest.raises(AttributeError):
            notation.shape = "national"  # type: ignore[misc]

    def test_equality(self) -> None:
        """Verify value equality."""
        n1 = PhoneNotation(shape="e164", value="15551234567")
        n2 = PhoneNotation(shape="e164", value="15551234567")
        assert n1 == n2

    def test_inequality(self) -> None:
        """Verify different values are not equal."""
        n1 = PhoneNotation(shape="e164", value="15551234567")
        n2 = PhoneNotation(shape="e164", value="15551234568")
        assert n1 != n2

    def test_hashable(self) -> None:
        """Verify it can be used in sets or as dict keys."""
        n1 = PhoneNotation(shape="e164", value="15551234567")
        n2 = PhoneNotation(shape="e164", value="15551234567")
        s = {n1, n2}
        assert len(s) == 1
        d = {n1: "value"}
        assert d[n2] == "value"


class TestPhoneContract:
    """Tests for PhoneContract dataclass."""

    def test_default_capability_name(self) -> None:
        """Verify capability_name is fixed to 'phone'."""
        contract = PhoneContract()
        assert contract.capability_name == "phone"

    def test_capability_name_not_settable(self) -> None:
        """Verify capability_name is not user-settable."""
        with pytest.raises(TypeError):
            PhoneContract(capability_name="other")  # type: ignore[call-arg]

    def test_default_excluded_rules(self) -> None:
        """Verify excluded_rules defaults to empty tuple."""
        contract = PhoneContract()
        assert contract.excluded_rules == ()

    def test_default_pinned_rules(self) -> None:
        """Verify pinned_rules defaults to None."""
        contract = PhoneContract()
        assert contract.pinned_rules is None

    def test_default_year(self) -> None:
        """Verify year defaults to None."""
        contract = PhoneContract()
        assert contract.year is None

    def test_default_output_format(self) -> None:
        """Verify output_format defaults to 'e164'."""
        contract = PhoneContract()
        assert contract.output_format == "e164"

    def test_default_country_none(self) -> None:
        """Verify default_country defaults to None."""
        contract = PhoneContract()
        assert contract.default_country is None

    def test_custom_default_country(self) -> None:
        """Verify default_country can be set."""
        contract = PhoneContract(default_country="US")
        assert contract.default_country == "US"

    def test_custom_output_format(self) -> None:
        """Verify output_format can be set."""
        contract = PhoneContract(output_format="rfc3966")
        assert contract.output_format == "rfc3966"

    def test_active_grammars_defaults_to_all_shipped(self) -> None:
        """No override: the engine runs every shipped grammar (fallback)."""
        contract = PhoneContract()
        assert contract.active_grammars is None
        assert [g.name for g in PhoneCapability().get_grammars()] == [
            "e164_recognition",
            "tel_uri_recognition",
            "international_00_recognition",
            "national_recognition",
        ]

    def test_is_frozen(self) -> None:
        """Verify immutability."""
        contract = PhoneContract()
        with pytest.raises(AttributeError):
            contract.year = 2024  # type: ignore[misc]


class TestPhoneCapability:
    """Tests for PhoneCapability wiring."""

    def test_is_capability_subclass(self) -> None:
        """Verify inheritance from base Capability."""
        assert issubclass(PhoneCapability, Capability)

    def test_name(self) -> None:
        """Verify capability name."""
        assert PhoneCapability.name == "phone"

    def test_get_grammars_returns_all(self) -> None:
        """Verify grammar count."""
        capability = PhoneCapability()
        grammars = capability.get_grammars()
        assert len(grammars) == 4

    def test_get_rules_returns_all(self) -> None:
        """Verify rule count."""
        capability = PhoneCapability()
        rules = capability.get_rules()
        assert len(rules) == 5

    def test_grammar_name(self) -> None:
        """Verify grammar names follow convention."""
        capability = PhoneCapability()
        names = {g.name for g in capability.get_grammars()}
        assert names == {
            "e164_recognition",
            "tel_uri_recognition",
            "international_00_recognition",
            "national_recognition",
        }

    def test_rule_name(self) -> None:
        """Verify rule names follow convention."""
        capability = PhoneCapability()
        names = {r.name for r in capability.get_rules()}
        assert names == {
            "Section 6.1-international-number",
            "Section 6.2-country-code",
            "Section 3-tel-uri",
            "Section 1.1-nanp-structure",
            "Section 1.2-service-npa",
        }

    def test_create_contract_default(self) -> None:
        """Verify create_contract factory defaults."""
        contract = PhoneCapability.create_contract()
        assert contract.capability_name == "phone"
        assert contract.default_country is None
        assert contract.output_format == "e164"

    def test_create_contract_with_params(self) -> None:
        """Verify create_contract factory passes parameters."""
        contract = PhoneCapability.create_contract(
            default_country="US",
            output_format="rfc3966",
            excluded_rules=["Section 1.2-service-npa"],
        )
        assert contract.default_country == "US"
        assert contract.output_format == "rfc3966"
        assert contract.excluded_rules == ("Section 1.2-service-npa",)


class TestPhoneCapabilityFormatValue:
    """Tests for PhoneCapability.format_value()."""

    NOTATION = PhoneNotation(shape="e164", value="15551234567")

    def test_e164_is_identity(self) -> None:
        """The default e164 path returns the canonical value unchanged."""
        cap = PhoneCapability()
        assert cap.format_value("+15551234567", "e164", self.NOTATION) == "+15551234567"

    def test_default_format_is_identity(self) -> None:
        """An unset output format returns the canonical value unchanged."""
        cap = PhoneCapability()
        assert cap.format_value("+15551234567", None, self.NOTATION) == "+15551234567"

    def test_rfc3966_renders_tel_uri(self) -> None:
        """RFC 3966 rendering wraps the canonical value in a tel: URI."""
        cap = PhoneCapability()
        assert (
            cap.format_value("+15551234567", "rfc3966", self.NOTATION)
            == "tel:+15551234567"
        )

    def test_national_strips_country_code(self) -> None:
        """National rendering strips the embedded country code."""
        cap = PhoneCapability()
        assert (
            cap.format_value("+15551234567", "national", self.NOTATION) == "5551234567"
        )

    def test_rfc3966_preserves_extension(self) -> None:
        """RFC 3966 rendering appends ;ext= when the notation carries one."""
        cap = PhoneCapability()
        notation = PhoneNotation(shape="rfc3966", value="15551234567", extension="890")
        assert (
            cap.format_value("+15551234567", "rfc3966", notation)
            == "tel:+15551234567;ext=890"
        )

    def test_national_uses_longest_country_code_prefix(self) -> None:
        """Taiwan (886) splits as 886, not 86 (China) plus a stray digit."""
        cap = PhoneCapability()
        notation = PhoneNotation(shape="e164", value="886212345678")
        assert cap.format_value("+886212345678", "national", notation) == "212345678"

    def test_defensive_passthrough_when_no_country_code_splits(self) -> None:
        """National rendering passes the value through when no prefix splits."""
        cap = PhoneCapability()
        notation = PhoneNotation(shape="e164", value="999123456789")
        assert (
            cap.format_value("+999123456789", "national", notation) == "+999123456789"
        )


class TestPhoneContractValidation:
    """Tests for PhoneContract __post_init__ validation."""

    def test_rejects_unknown_output_format(self) -> None:
        """Unsupported output_format raises ContractError."""
        with pytest.raises(ContractError):
            PhoneContract(output_format="uppercase")

    def test_rejects_lowercase_output_format(self) -> None:
        """output_format is case-sensitive and must be one of the enum values."""
        with pytest.raises(ContractError):
            PhoneContract(output_format="E164")

    def test_accepts_all_valid_output_formats(self) -> None:
        """All documented output formats construct successfully."""
        assert PhoneContract(output_format="e164").output_format == "e164"
        assert PhoneContract(output_format="rfc3966").output_format == "rfc3966"
        # "national" requires default_country to be a NANP country (ADR-0010
        # re-entry: bare NSN without country cannot re-enter).
        with pytest.raises(ContractError):
            PhoneContract(output_format="national")
        with pytest.raises(ContractError):
            PhoneContract(output_format="national", default_country="GB")
        with_country = PhoneContract(default_country="US", output_format="national")
        assert with_country.output_format == "national"

    def test_accepts_default_output_format(self) -> None:
        """'default' reverts to the default e164 output."""
        contract = PhoneContract(output_format="default")
        assert contract.output_format == "e164"

    @pytest.mark.parametrize("fmt", ["none", ""])
    def test_rejects_none_and_empty_string(self, fmt: str) -> None:
        """'none' and '' are contract violations, not silent no-ops."""
        with pytest.raises(ContractError):
            PhoneContract(output_format=fmt)

    def test_rejects_non_alpha2_default_country(self) -> None:
        """default_country must be an uppercase ISO 3166-1 alpha-2 code."""
        with pytest.raises(ContractError):
            PhoneContract(default_country="us")

    def test_rejects_non_string_output_format(self) -> None:
        """Non-string output_format raises ContractError, not TypeError."""
        with pytest.raises(ContractError):
            PhoneContract(output_format=["e164"])  # type: ignore[arg-type]

    def test_rejects_non_string_default_country(self) -> None:
        """Non-string default_country raises ContractError, not TypeError."""
        with pytest.raises(ContractError):
            PhoneContract(default_country=5)  # type: ignore[arg-type]

    def test_rejects_invalid_length_default_country(self) -> None:
        """default_country must be exactly 2 letters."""
        with pytest.raises(ContractError):
            PhoneContract(default_country="USA")


class TestPhoneNationalOutput:
    """E2E behavior for output_format='national' (ADR-0010).

    ``national`` requires ``default_country`` to be a NANP country so the
    rendered NSN can re-enter under the same contract. Rendering without a
    country is rejected at construction (ContractError) — a default
    (country-less) contract can never produce a non-re-enterable ``national`` V.
    """

    def setup_method(self) -> None:
        """Register the Phone capability for each test."""
        reset_registry()
        register_capability(PhoneCapability())

    def teardown_method(self) -> None:
        """Reset the registry so other tests start clean."""
        reset_registry()

    def test_national_requires_default_country(self) -> None:
        """'national' without a NANP default_country is rejected at construction."""
        with pytest.raises(ContractError):
            PhoneContract(output_format="national")
        with pytest.raises(ContractError):
            PhoneContract(output_format="national", default_country="GB")

    def test_national_from_e164_with_default_country(self) -> None:
        """'+12125551234' → '2125551234' with default_country='US' (non-fictional)."""
        contract = PhoneContract(output_format="national", default_country="US")
        result = canonicalize("+12125551234", contract)
        assert result.status == Resolution.SUCCESS
        assert result.canonicalized_value == "2125551234"

    def test_national_from_tel_uri_with_default_country(self) -> None:
        """'tel:+12125551234' → '2125551234' with default_country='US'."""
        contract = PhoneContract(output_format="national", default_country="US")
        result = canonicalize("tel:+12125551234", contract)
        assert result.status == Resolution.SUCCESS
        assert result.canonicalized_value == "2125551234"
