"""Tests for Phone capability."""

import pytest

from paxman.api import canonicalize
from paxman.capabilities.Phone.capability import PhoneCapability
from paxman.capabilities.Phone.contract import PhoneContract
from paxman.capabilities.Phone.notation import PhoneNotation
from paxman.capabilities.Phone.rules.data.e164_country_codes import (
    split_country_code,
)
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

    def test_split_renders_plus_cc_space_nsn(self) -> None:
        """Split rendering inserts one space between country code and NSN."""
        cap = PhoneCapability()
        assert (
            cap.format_value("+15551234567", "split", self.NOTATION) == "+1 5551234567"
        )

    def test_rfc3966_preserves_extension(self) -> None:
        """RFC 3966 rendering appends ;ext= when the notation carries one."""
        cap = PhoneCapability()
        notation = PhoneNotation(shape="rfc3966", value="15551234567", extension="890")
        assert (
            cap.format_value("+15551234567", "rfc3966", notation)
            == "tel:+15551234567;ext=890"
        )

    def test_split_ignores_extension(self) -> None:
        """Split rendering never appends ;ext=, even when noted."""
        cap = PhoneCapability()
        notation = PhoneNotation(shape="rfc3966", value="15551234567", extension="890")
        assert (
            cap.format_value("+15551234567", "split", notation) == "+1 5551234567"
        )

    def test_split_uses_longest_country_code_prefix(self) -> None:
        """Taiwan (886) splits as 886, not 86 (China) plus a stray digit."""
        cap = PhoneCapability()
        notation = PhoneNotation(shape="e164", value="886212345678")
        assert (
            cap.format_value("+886212345678", "split", notation) == "+886 212345678"
        )
        assert split_country_code("886212345678") == "886"

    def test_split_uniform_for_non_nanp(self) -> None:
        """Non-NANP renders the same +CC NSN shape — no preservation branch."""
        cap = PhoneCapability()
        notation = PhoneNotation(shape="e164", value="442079460958")
        assert (
            cap.format_value("+442079460958", "split", notation) == "+44 2079460958"
        )

    def test_defensive_passthrough_when_no_country_code_splits(self) -> None:
        """Split rendering passes the value through when no prefix splits."""
        cap = PhoneCapability()
        notation = PhoneNotation(shape="e164", value="999123456789")
        assert (
            cap.format_value("+999123456789", "split", notation) == "+999123456789"
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
        assert PhoneContract(output_format="split").output_format == "split"
        # "national" was de-offered per ADR-0011 — rejected with a migration
        # message naming "split", even with a NANP default_country.
        with pytest.raises(ContractError, match="split"):
            PhoneContract(output_format="national")
        with pytest.raises(ContractError, match="split"):
            PhoneContract(output_format="national", default_country="US")

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


class TestPhoneSplitContract:
    """Contract surface for output_format='split' (ADR-0011 Phase 2).

    ``national`` was de-offered: it dropped the country code and could not
    re-enter under the default contract. Construction with
    ``output_format="national"`` is rejected with a migration message naming
    ``split``. Offered surface is ``rfc3966`` + ``split``.
    """

    def test_national_removed_with_migration_message(self) -> None:
        """'national' raises ContractError naming 'split', with or without country."""
        with pytest.raises(ContractError, match="split"):
            PhoneContract(output_format="national")
        with pytest.raises(ContractError, match="split"):
            PhoneContract(output_format="national", default_country="US")

    def test_offered_formats_set(self) -> None:
        """OFFERED_OUTPUT_FORMATS is exactly rfc3966 + split."""
        assert PhoneContract.OFFERED_OUTPUT_FORMATS == frozenset({"rfc3966", "split"})

    def test_split_resolves(self) -> None:
        """'split' constructs and resolves to itself."""
        assert PhoneContract(output_format="split").output_format == "split"


class TestPhoneSplitOutput:
    """E2E behavior for output_format='split' (ADR-0011 Phase 2).

    ``split`` renders ``+CC NSN`` (single space, uniform for every country
    code) and re-enters param-free through the existing E.164 grammar.
    """

    def setup_method(self) -> None:
        """Register the Phone capability for each test."""
        reset_registry()
        register_capability(PhoneCapability())

    def teardown_method(self) -> None:
        """Reset the registry so other tests start clean."""
        reset_registry()

    def test_split_nanp(self) -> None:
        """'+12125551234' → '+1 2125551234' (non-fictional)."""
        contract = PhoneContract(output_format="split")
        result = canonicalize("+12125551234", contract)
        assert result.status == Resolution.SUCCESS
        assert result.canonicalized_value == "+1 2125551234"

    def test_split_non_nanp_uniform(self) -> None:
        """'+4412341234' → '+44 12341234' — same shape as NANP, no branch."""
        contract = PhoneContract(output_format="split")
        result = canonicalize("+4412341234", contract)
        assert result.status == Resolution.SUCCESS
        assert result.canonicalized_value == "+44 12341234"

    def test_split_extension_ignored(self) -> None:
        """A tel: URI extension never surfaces in split output."""
        contract = PhoneContract(output_format="split")
        result = canonicalize("tel:+12125551234;ext=45", contract)
        assert result.status == Resolution.SUCCESS
        assert result.canonicalized_value == "+1 2125551234"

    def test_split_round_trip(self) -> None:
        """A split render re-enters under the default contract (param-free)."""
        contract = PhoneContract(output_format="split")
        first = canonicalize("+12125551234", contract)
        assert first.status == Resolution.SUCCESS
        assert first.canonicalized_value == "+1 2125551234"
        second = canonicalize("+1 2125551234", PhoneContract())
        assert second.status == Resolution.SUCCESS
        assert second.canonicalized_value == "+12125551234"

    def test_split_injective_across_country_codes(self) -> None:
        """GB '+4412341234' and MY '+6012341234' render distinctly."""
        contract = PhoneContract(output_format="split")
        gb = canonicalize("+4412341234", contract)
        my = canonicalize("+6012341234", contract)
        assert gb.status == Resolution.SUCCESS
        assert my.status == Resolution.SUCCESS
        assert gb.canonicalized_value == "+44 12341234"
        assert my.canonicalized_value == "+60 12341234"
        assert gb.canonicalized_value != my.canonicalized_value

    def test_format_value_split_identity_equivalence(self) -> None:
        """The default contract still renders E.164 identity."""
        cap = PhoneCapability()
        notation = PhoneNotation(shape="e164", value="12125551234")
        assert (
            cap.format_value("+12125551234", "e164", notation) == "+12125551234"
        )
