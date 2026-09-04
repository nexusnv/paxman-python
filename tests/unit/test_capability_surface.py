"""Every exported capability exposes the unanimous contract/capability surface."""

from __future__ import annotations

import inspect
from inspect import Parameter

import pytest

from paxman.capabilities.BIC.capability import BICCapability
from paxman.capabilities.BIC.contract import BICContract
from paxman.capabilities.Coordinates.capability import CoordinatesCapability
from paxman.capabilities.Coordinates.contract import CoordinatesContract
from paxman.capabilities.Country.capability import CountryCapability
from paxman.capabilities.Country.contract import CountryContract
from paxman.capabilities.Country.notation import CountryNotation
from paxman.capabilities.Currency.capability import CurrencyCapability
from paxman.capabilities.Currency.contract import CurrencyContract
from paxman.capabilities.Currency.notation import CurrencyNotation
from paxman.capabilities.Date.capability import DateCapability
from paxman.capabilities.Date.contract import DateContract
from paxman.capabilities.Date.notation import DateNotation
from paxman.capabilities.Element.capability import ElementCapability
from paxman.capabilities.Element.contract import ElementContract
from paxman.capabilities.Email.capability import EmailCapability
from paxman.capabilities.Email.contract import EmailContract
from paxman.capabilities.Email.notation import EmailNotation
from paxman.capabilities.IBAN.capability import IBANCapability
from paxman.capabilities.IBAN.contract import IBANContract
from paxman.capabilities.IP.capability import IPCapability
from paxman.capabilities.IP.contract import IPContract
from paxman.capabilities.IP.notation import IPNotation
from paxman.capabilities.ISBN.capability import ISBNCapability
from paxman.capabilities.ISBN.contract import ISBNContract
from paxman.capabilities.ISBN.notation import ISBNNotation
from paxman.capabilities.ISSN.capability import ISSNCapability
from paxman.capabilities.ISSN.contract import ISSNContract
from paxman.capabilities.ISSN.notation import ISSNNotation
from paxman.capabilities.Language.capability import LanguageCapability
from paxman.capabilities.Language.contract import LanguageContract
from paxman.capabilities.MacAddress.capability import MacAddressCapability
from paxman.capabilities.MacAddress.contract import MacAddressContract
from paxman.capabilities.Money.capability import MoneyCapability
from paxman.capabilities.Money.contract import MoneyContract
from paxman.capabilities.Money.notation import MoneyNotation
from paxman.capabilities.ORCID.capability import ORCIDCapability
from paxman.capabilities.ORCID.contract import ORCIDContract
from paxman.capabilities.Phone.capability import PhoneCapability
from paxman.capabilities.Phone.contract import PhoneContract
from paxman.capabilities.Phone.notation import PhoneNotation
from paxman.capabilities.SIUnit.capability import SIUnitCapability
from paxman.capabilities.SIUnit.contract import SIUnitContract
from paxman.capabilities.SIUnit.notation import SIUnitNotation
from paxman.capabilities.URL.capability import URLCapability
from paxman.capabilities.URL.contract import URLCapabilityContract
from paxman.capabilities.URL.notation import URLNotation
from paxman.core.capability import ContractFactory
from paxman.core.capability_contract import CapabilityContract

_COMMON_BLOCK = (
    "excluded_rules",
    "pinned_rules",
    "year",
    "output_format",
    "extra_grammars",
)

_CAPABILITY_SURFACES = [
    pytest.param(
        EmailCapability,
        EmailContract,
        "email",
        id="email",
    ),
    pytest.param(
        ElementCapability,
        ElementContract,
        "symbol",
        id="element",
    ),
    pytest.param(
        CoordinatesCapability,
        CoordinatesContract,
        "decimal",
        id="coordinates",
    ),
    pytest.param(
        BICCapability,
        BICContract,
        "bic",
        id="bic",
    ),
    pytest.param(
        DateCapability,
        DateContract,
        "ISO",
        id="date",
    ),
    pytest.param(
        CountryCapability,
        CountryContract,
        "alpha2",
        id="country",
    ),
    pytest.param(
        CurrencyCapability,
        CurrencyContract,
        "code",
        id="currency",
    ),
    pytest.param(
        IPCapability,
        IPContract,
        "ip",
        id="ip",
    ),
    pytest.param(
        IBANCapability,
        IBANContract,
        "electronic",
        id="iban",
    ),
    pytest.param(
        ISBNCapability,
        ISBNContract,
        "isbn13",
        id="isbn",
    ),
    pytest.param(
        MoneyCapability,
        MoneyContract,
        "code_amount",
        id="money",
    ),
    pytest.param(
        MacAddressCapability,
        MacAddressContract,
        "colon",
        id="mac_address",
    ),
    pytest.param(
        LanguageCapability,
        LanguageContract,
        "bcp47",
        id="language",
    ),
    pytest.param(
        ORCIDCapability,
        ORCIDContract,
        "orcid",
        id="orcid",
    ),
    pytest.param(
        ISSNCapability,
        ISSNContract,
        "hyphenated",
        id="issn",
    ),
    pytest.param(
        PhoneCapability,
        PhoneContract,
        "e164",
        id="phone",
    ),
    pytest.param(
        SIUnitCapability,
        SIUnitContract,
        "symbol",
        id="si_unit",
    ),
    pytest.param(
        URLCapability,
        URLCapabilityContract,
        "url",
        id="url",
    ),
]


class TestContractHomogeneity:
    @pytest.mark.unit
    @pytest.mark.parametrize(
        "_capability,_contract_class,_default_format",
        _CAPABILITY_SURFACES,
    )
    def test_contracts_inherit_capability_contract(
        self,
        _capability: type[object],
        _contract_class: type[object],
        _default_format: str,
    ) -> None:
        """Every contract class inherits CapabilityContract."""
        assert issubclass(_contract_class, CapabilityContract)

    @pytest.mark.unit
    @pytest.mark.parametrize(
        "_capability,_contract_class,_default_format",
        _CAPABILITY_SURFACES,
    )
    def test_capabilities_satisfy_contract_factory(
        self,
        _capability: type[object],
        _contract_class: type[object],
        _default_format: str,
    ) -> None:
        """Every capability class satisfies the ContractFactory protocol."""
        assert isinstance(_capability, ContractFactory)

    @pytest.mark.unit
    @pytest.mark.parametrize(
        "_capability,_contract_class,_default_format",
        _CAPABILITY_SURFACES,
    )
    def test_create_contract_signature_has_unanimous_common_block(
        self,
        _capability: type[object],
        _contract_class: type[object],
        _default_format: str,
    ) -> None:
        """create_contract parameters begin with the unanimous common block.

        The runtime_checkable ``ContractFactory`` protocol only checks
        attribute presence, not the signature — so this test pins the actual
        parameter shape: the first five parameters, in order, are
        ``excluded_rules, pinned_rules, year, output_format, extra_grammars``
        and every parameter is keyword-only.
        """
        parameters = list(
            inspect.signature(_capability.create_contract).parameters.values()
        )
        assert [parameter.name for parameter in parameters[:5]] == list(_COMMON_BLOCK)
        assert len(parameters) >= 5
        assert all(parameter.kind == Parameter.KEYWORD_ONLY for parameter in parameters)

    @pytest.mark.unit
    @pytest.mark.parametrize(
        "_capability,_contract_class,_default_format",
        _CAPABILITY_SURFACES,
    )
    def test_output_format_optional_in_contract_signature(
        self,
        _capability: type[object],
        _contract_class: type[object],
        _default_format: str,
    ) -> None:
        """output_format defaults to None on every contract __init__."""
        parameters = inspect.signature(_contract_class).parameters
        assert parameters["output_format"].default is None

    @pytest.mark.unit
    @pytest.mark.parametrize(
        "_capability,_contract_class,_default_format",
        _CAPABILITY_SURFACES,
    )
    def test_output_format_none_resolves_to_concrete_default(
        self,
        _capability: type[object],
        _contract_class: type[object],
        _default_format: str,
    ) -> None:
        """A no-arg contract resolves output_format to the concrete default."""
        assert _contract_class().output_format == _default_format

    @pytest.mark.unit
    @pytest.mark.parametrize(
        "_capability,_contract_class,_default_format",
        _CAPABILITY_SURFACES,
    )
    def test_extra_grammars_defaults_to_empty_on_concrete_contracts(
        self,
        _capability: type[object],
        _contract_class: type[object],
        _default_format: str,
    ) -> None:
        """A no-arg contract opts into no community grammars."""
        assert _contract_class().extra_grammars == ()

    @pytest.mark.unit
    @pytest.mark.parametrize(
        "_capability,_contract_class,_default_format",
        _CAPABILITY_SURFACES,
    )
    def test_create_contract_forwards_extra_grammars_in_order(
        self,
        _capability: type[object],
        _contract_class: type[object],
        _default_format: str,
    ) -> None:
        """create_contract passes extra_grammars through, order preserved."""
        contract = _capability.create_contract(extra_grammars=["first", "second"])
        assert contract.extra_grammars == ("first", "second")

    @pytest.mark.unit
    @pytest.mark.parametrize(
        "_capability,_contract_class,_default_format",
        _CAPABILITY_SURFACES,
    )
    def test_contracts_expose_no_serialization_hooks(
        self,
        _capability: type[object],
        _contract_class: type[object],
        _default_format: str,
    ) -> None:
        """No concrete contract resurrects the removed serialization hooks.

        The negative locks in ``test_capability_contract.py`` pin the base
        class, but a re-added override on a single concrete contract would
        slip past them; this guard pins every shipped concrete contract.
        """
        assert not hasattr(_contract_class, "as_dict")
        assert not hasattr(_contract_class, "_extra_dict_fields")

    @pytest.mark.unit
    def test_surface_covers_every_exported_capability(self) -> None:
        """The surface guard tracks the package's registration surface.

        ``paxman.capabilities.__all__`` is the registration surface: every
        capability exported there must appear in ``_CAPABILITY_SURFACES``,
        and every guarded capability must be exported. This prevents a
        registered capability from silently narrowing the homogeneity
        mandate (ISBN slipped through PR #12 this way).
        """
        import importlib

        import paxman.capabilities as capabilities

        surface_names = {param.values[0].name for param in _CAPABILITY_SURFACES}
        exported_names = set()
        for name in capabilities.__all__:
            obj = getattr(capabilities, name)
            # If the package was already imported as a submodule, getattr
            # returns the package, not the lazy class. Resolve via _LAZY.
            if hasattr(obj, "__path__"):
                mod_name, attr = capabilities._LAZY[name]
                obj = getattr(importlib.import_module(mod_name), attr)
            exported_names.add(obj.name)  # type: ignore[attr-defined]
        assert surface_names == exported_names


# ---------------------------------------------------------------------------
# format_value surface: one formatter per capability, offered formats handled
# ---------------------------------------------------------------------------

# Real instances + concrete notations per capability. The canonical value is
# the rule-produced default representation; expectations are independent
# literals (not derived from the formatter under test).
_FORMAT_SURFACES = [
    pytest.param(
        EmailCapability,
        EmailContract,
        "user@example.com",
        EmailNotation(local_part="user", domain_part="example.com"),
        id="email",
    ),
    pytest.param(
        DateCapability,
        DateContract,
        "2026-01-15",
        DateNotation(N1="2026", N2="01", N3="15"),
        id="date",
    ),
    pytest.param(
        CountryCapability,
        CountryContract,
        "DE",
        CountryNotation(shape="alpha2", value="DE"),
        id="country",
    ),
    pytest.param(
        CurrencyCapability,
        CurrencyContract,
        "USD",
        CurrencyNotation(text="USD", shape="code"),
        id="currency",
    ),
    pytest.param(
        IPCapability,
        IPContract,
        "192.0.2.1",
        IPNotation(address="192.0.2.1"),
        id="ip",
    ),
    pytest.param(
        ISBNCapability,
        ISBNContract,
        "9780306406157",
        ISBNNotation(shape="isbn13", digits="9780306406157"),
        id="isbn",
    ),
    pytest.param(
        ISSNCapability,
        ISSNContract,
        "0317-8471",
        ISSNNotation(digits="03178471"),
        id="issn",
    ),
    pytest.param(
        MoneyCapability,
        MoneyContract,
        "USD 500.00",
        MoneyNotation(
            currency_part="USD",
            amount_part="500",
            currency_shape="code",
            amount_shape="integer",
        ),
        id="money",
    ),
    pytest.param(
        PhoneCapability,
        PhoneContract,
        "+15551234567",
        PhoneNotation(shape="e164", value="15551234567"),
        id="phone",
    ),
    pytest.param(
        SIUnitCapability,
        SIUnitContract,
        "m",
        SIUnitNotation(text="m", shape="symbol"),
        id="si_unit",
    ),
    pytest.param(
        URLCapability,
        URLCapabilityContract,
        "https://example.com/a%20b",
        URLNotation(text="https://example.com/a%20b"),
        id="url",
    ),
]

# Capabilities with non-empty OFFERED_OUTPUT_FORMATS, and the independent
# literal each offered format must render for the sample canonical value.
_FORMATTED_EXPECTATIONS = [
    pytest.param(
        DateCapability,
        DateContract,
        "2026-01-15",
        DateNotation(N1="2026", N2="01", N3="15"),
        {"US": "01/15/2026"},
        id="date",
    ),
    pytest.param(
        CountryCapability,
        CountryContract,
        "DE",
        CountryNotation(shape="alpha2", value="DE"),
        {"alpha3": "DEU", "numeric": "276", "name": "GERMANY"},
        id="country",
    ),
    pytest.param(
        ISBNCapability,
        ISBNContract,
        "9780306406157",
        ISBNNotation(shape="isbn13", digits="9780306406157"),
        {"hyphenated": "978-0-306-40615-7"},
        id="isbn",
    ),
    pytest.param(
        ISSNCapability,
        ISSNContract,
        "0317-8471",
        ISSNNotation(digits="03178471"),
        {"compact": "03178471", "urn": "urn:issn:0317-8471"},
        id="issn",
    ),
    pytest.param(
        MoneyCapability,
        MoneyContract,
        "USD 500.00",
        MoneyNotation(
            currency_part="USD",
            amount_part="500",
            currency_shape="code",
            amount_shape="integer",
        ),
        {"compact": "USD500.00"},
        id="money",
    ),
    pytest.param(
        PhoneCapability,
        PhoneContract,
        "+15551234567",
        PhoneNotation(shape="e164", value="15551234567"),
        {"rfc3966": "tel:+15551234567", "national": "5551234567"},
        id="phone",
    ),
]

# Capabilities that offer no alternative formats: their formatter must be the
# identity regardless of the requested format.
_IDENTITY_SURFACES = [
    pytest.param(
        EmailCapability,
        EmailContract,
        "user@example.com",
        EmailNotation(local_part="user", domain_part="example.com"),
        id="email",
    ),
    pytest.param(
        CurrencyCapability,
        CurrencyContract,
        "USD",
        CurrencyNotation(text="USD", shape="code"),
        id="currency",
    ),
    pytest.param(
        IPCapability,
        IPContract,
        "192.0.2.1",
        IPNotation(address="192.0.2.1"),
        id="ip",
    ),
    pytest.param(
        SIUnitCapability,
        SIUnitContract,
        "m",
        SIUnitNotation(text="m", shape="symbol"),
        id="si_unit",
    ),
    pytest.param(
        URLCapability,
        URLCapabilityContract,
        "https://example.com/a%20b",
        URLNotation(text="https://example.com/a%20b"),
        id="url",
    ),
]


class TestFormatValueSurface:
    @pytest.mark.unit
    @pytest.mark.parametrize(
        "_capability,_contract_class,_canonical,_notation",
        _FORMAT_SURFACES,
    )
    def test_formatter_default_agrees_with_contract_default(
        self,
        _capability: type[object],
        _contract_class: type[object],
        _canonical: str,
        _notation: object,
    ) -> None:
        """Rendering in the contract's default format keeps the value."""
        capability = _capability()
        default_format = _contract_class.DEFAULT_OUTPUT_FORMAT
        assert capability.format_value(_canonical, default_format, _notation) == (
            _canonical
        )

    @pytest.mark.unit
    @pytest.mark.parametrize(
        "_capability,_contract_class,_canonical,_notation,_expected_by_format",
        _FORMATTED_EXPECTATIONS,
    )
    def test_every_offered_format_renders_expected_value(
        self,
        _capability: type[object],
        _contract_class: type[object],
        _canonical: str,
        _notation: object,
        _expected_by_format: dict[str, str],
    ) -> None:
        """Each offered format is handled by the formatter.

        The expectation table must cover exactly the capability's offered
        formats: a newly offered format with no expectation (or a stale
        expectation for a withdrawn format) fails the set-equality guard.
        """
        assert set(_contract_class.OFFERED_OUTPUT_FORMATS) == set(_expected_by_format)
        capability = _capability()
        for output_format, expected in _expected_by_format.items():
            assert (
                capability.format_value(_canonical, output_format, _notation)
                == expected
            )

    @pytest.mark.unit
    @pytest.mark.parametrize(
        "_capability,_contract_class,_canonical,_notation",
        _IDENTITY_SURFACES,
    )
    def test_no_offered_format_capabilities_are_identity(
        self,
        _capability: type[object],
        _contract_class: type[object],
        _canonical: str,
        _notation: object,
    ) -> None:
        """Email/IP offer no formats; the formatter leaves the value unchanged."""
        assert not _contract_class.OFFERED_OUTPUT_FORMATS
        capability = _capability()
        assert (
            capability.format_value(
                _canonical, _contract_class.DEFAULT_OUTPUT_FORMAT, _notation
            )
            == _canonical
        )
        assert capability.format_value(_canonical, None, _notation) == _canonical
