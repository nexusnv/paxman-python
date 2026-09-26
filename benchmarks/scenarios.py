"""Benchmark scenarios — one deterministic input per capability (Item 7).

Inputs chosen to exercise the hot path: recognition + validation + formatting.
No network, no clock, no randomness — deterministic per library snapshot.
"""

from __future__ import annotations


def _bic_register() -> None:
    from paxman.capabilities import BIC
    from paxman.core.discovery import get_capability, register_capability
    from paxman.core.errors import CapabilityError

    try:
        get_capability("bic")
    except CapabilityError:
        register_capability(BIC())


def _bic_contract() -> object:
    from paxman.capabilities import BIC

    return BIC.create_contract()


def _chemical_element_register() -> None:
    from paxman.capabilities import ChemicalElement
    from paxman.core.discovery import get_capability, register_capability
    from paxman.core.errors import CapabilityError

    try:
        get_capability("chemical_element")
    except CapabilityError:
        register_capability(ChemicalElement())


def _chemical_element_contract() -> object:
    from paxman.capabilities import ChemicalElement

    return ChemicalElement.create_contract()


def _coordinates_register() -> None:
    from paxman.capabilities import Coordinates
    from paxman.core.discovery import get_capability, register_capability
    from paxman.core.errors import CapabilityError

    try:
        get_capability("coordinates")
    except CapabilityError:
        register_capability(Coordinates())


def _coordinates_contract() -> object:
    from paxman.capabilities import Coordinates

    return Coordinates.create_contract()


def _country_register() -> None:
    from paxman.capabilities import Country
    from paxman.core.discovery import get_capability, register_capability
    from paxman.core.errors import CapabilityError

    try:
        get_capability("country")
    except CapabilityError:
        register_capability(Country())


def _country_contract() -> object:
    from paxman.capabilities import Country

    return Country.create_contract()


def _credit_card_register() -> None:
    from paxman.capabilities import CreditCard
    from paxman.core.discovery import get_capability, register_capability
    from paxman.core.errors import CapabilityError

    try:
        get_capability("credit_card")
    except CapabilityError:
        register_capability(CreditCard())


def _credit_card_contract() -> object:
    from paxman.capabilities import CreditCard

    return CreditCard.create_contract()


def _currency_register() -> None:
    from paxman.capabilities import Currency
    from paxman.core.discovery import get_capability, register_capability
    from paxman.core.errors import CapabilityError

    try:
        get_capability("currency")
    except CapabilityError:
        register_capability(Currency())


def _currency_contract() -> object:
    from paxman.capabilities import Currency

    return Currency.create_contract()


def _date_register() -> None:
    from paxman.capabilities import Date
    from paxman.core.discovery import get_capability, register_capability
    from paxman.core.errors import CapabilityError

    try:
        get_capability("date")
    except CapabilityError:
        register_capability(Date())


def _date_contract() -> object:
    from paxman.capabilities import Date

    return Date.create_contract()


def _doi_register() -> None:
    from paxman.capabilities import DOI
    from paxman.core.discovery import get_capability, register_capability
    from paxman.core.errors import CapabilityError

    try:
        get_capability("doi")
    except CapabilityError:
        register_capability(DOI())


def _doi_contract() -> object:
    from paxman.capabilities import DOI

    return DOI.create_contract()


def _domain_register() -> None:
    from paxman.capabilities import Domain
    from paxman.core.discovery import get_capability, register_capability
    from paxman.core.errors import CapabilityError

    try:
        get_capability("domain")
    except CapabilityError:
        register_capability(Domain())


def _domain_contract() -> object:
    from paxman.capabilities import Domain

    return Domain.create_contract()


def _email_register() -> None:
    from paxman.capabilities import Email
    from paxman.core.discovery import get_capability, register_capability
    from paxman.core.errors import CapabilityError

    try:
        get_capability("email")
    except CapabilityError:
        register_capability(Email())


def _email_contract() -> object:
    from paxman.capabilities import Email

    return Email.create_contract()


def _gtin_register() -> None:
    from paxman.capabilities import GTIN
    from paxman.core.discovery import get_capability, register_capability
    from paxman.core.errors import CapabilityError

    try:
        get_capability("gtin")
    except CapabilityError:
        register_capability(GTIN())


def _gtin_contract() -> object:
    from paxman.capabilities import GTIN

    return GTIN.create_contract()


def _iban_register() -> None:
    from paxman.capabilities import IBAN
    from paxman.core.discovery import get_capability, register_capability
    from paxman.core.errors import CapabilityError

    try:
        get_capability("iban")
    except CapabilityError:
        register_capability(IBAN())


def _iban_contract() -> object:
    from paxman.capabilities import IBAN

    return IBAN.create_contract()


def _ip_register() -> None:
    from paxman.capabilities import IP
    from paxman.core.discovery import get_capability, register_capability
    from paxman.core.errors import CapabilityError

    try:
        get_capability("ip")
    except CapabilityError:
        register_capability(IP())


def _ip_contract() -> object:
    from paxman.capabilities import IP

    return IP.create_contract()


def _isbn_register() -> None:
    from paxman.capabilities import ISBN
    from paxman.core.discovery import get_capability, register_capability
    from paxman.core.errors import CapabilityError

    try:
        get_capability("isbn")
    except CapabilityError:
        register_capability(ISBN())


def _isbn_contract() -> object:
    from paxman.capabilities import ISBN

    return ISBN.create_contract()


def _isin_register() -> None:
    from paxman.capabilities import ISIN
    from paxman.core.discovery import get_capability, register_capability
    from paxman.core.errors import CapabilityError

    try:
        get_capability("isin")
    except CapabilityError:
        register_capability(ISIN())


def _isin_contract() -> object:
    from paxman.capabilities import ISIN

    return ISIN.create_contract()


def _issn_register() -> None:
    from paxman.capabilities import ISSN
    from paxman.core.discovery import get_capability, register_capability
    from paxman.core.errors import CapabilityError

    try:
        get_capability("issn")
    except CapabilityError:
        register_capability(ISSN())


def _issn_contract() -> object:
    from paxman.capabilities import ISSN

    return ISSN.create_contract()


def _language_register() -> None:
    from paxman.capabilities import Language
    from paxman.core.discovery import get_capability, register_capability
    from paxman.core.errors import CapabilityError

    try:
        get_capability("language")
    except CapabilityError:
        register_capability(Language())


def _language_contract() -> object:
    from paxman.capabilities import Language

    return Language.create_contract()


def _lei_register() -> None:
    from paxman.capabilities import LEI
    from paxman.core.discovery import get_capability, register_capability
    from paxman.core.errors import CapabilityError

    try:
        get_capability("lei")
    except CapabilityError:
        register_capability(LEI())


def _lei_contract() -> object:
    from paxman.capabilities import LEI

    return LEI.create_contract()


def _mac_address_register() -> None:
    from paxman.capabilities import MacAddress
    from paxman.core.discovery import get_capability, register_capability
    from paxman.core.errors import CapabilityError

    try:
        get_capability("mac_address")
    except CapabilityError:
        register_capability(MacAddress())


def _mac_address_contract() -> object:
    from paxman.capabilities import MacAddress

    return MacAddress.create_contract()


def _money_register() -> None:
    from paxman.capabilities import Money
    from paxman.core.discovery import get_capability, register_capability
    from paxman.core.errors import CapabilityError

    try:
        get_capability("money")
    except CapabilityError:
        register_capability(Money())


def _money_contract() -> object:
    from paxman.capabilities import Money

    return Money.create_contract()


def _orcid_register() -> None:
    from paxman.capabilities import ORCID
    from paxman.core.discovery import get_capability, register_capability
    from paxman.core.errors import CapabilityError

    try:
        get_capability("orcid")
    except CapabilityError:
        register_capability(ORCID())


def _orcid_contract() -> object:
    from paxman.capabilities import ORCID

    return ORCID.create_contract()


def _phone_register() -> None:
    from paxman.capabilities import Phone
    from paxman.core.discovery import get_capability, register_capability
    from paxman.core.errors import CapabilityError

    try:
        get_capability("phone")
    except CapabilityError:
        register_capability(Phone())


def _phone_contract() -> object:
    from paxman.capabilities import Phone

    return Phone.create_contract(default_country="US")


def _si_unit_register() -> None:
    from paxman.capabilities import SIUnit
    from paxman.core.discovery import get_capability, register_capability
    from paxman.core.errors import CapabilityError

    try:
        get_capability("si_unit")
    except CapabilityError:
        register_capability(SIUnit())


def _si_unit_contract() -> object:
    from paxman.capabilities import SIUnit

    return SIUnit.create_contract()


def _timezone_register() -> None:
    from paxman.capabilities import Timezone
    from paxman.core.discovery import get_capability, register_capability
    from paxman.core.errors import CapabilityError

    try:
        get_capability("timezone")
    except CapabilityError:
        register_capability(Timezone())


def _timezone_contract() -> object:
    from paxman.capabilities import Timezone

    return Timezone.create_contract()


def _url_register() -> None:
    from paxman.capabilities import URL
    from paxman.core.discovery import get_capability, register_capability
    from paxman.core.errors import CapabilityError

    try:
        get_capability("url")
    except CapabilityError:
        register_capability(URL())


def _url_contract() -> object:
    from paxman.capabilities import URL

    return URL.create_contract()


def _utc_offset_register() -> None:
    from paxman.capabilities import UtcOffset
    from paxman.core.discovery import get_capability, register_capability
    from paxman.core.errors import CapabilityError

    try:
        get_capability("utc_offset")
    except CapabilityError:
        register_capability(UtcOffset())


def _utc_offset_contract() -> object:
    from paxman.capabilities import UtcOffset

    return UtcOffset.create_contract()


def _uuid_register() -> None:
    from paxman.capabilities import UUID
    from paxman.core.discovery import get_capability, register_capability
    from paxman.core.errors import CapabilityError

    try:
        get_capability("uuid")
    except CapabilityError:
        register_capability(UUID())


def _uuid_contract() -> object:
    from paxman.capabilities import UUID

    return UUID.create_contract()


def _freeze_register() -> None:
    from paxman.api.bootstrap import register_all_shipped

    register_all_shipped()


def _freeze_contract() -> object:
    return object()


# Recognition-only payloads: si_unit over increasing text sizes (ADR Part IV)
# Deterministic, exercises the trie scan hot path without validation.
def _si_text(size: int) -> str:
    base = "kg " + "x " * 20
    return (base * ((size // len(base)) + 1))[:size]


_SI_64B = _si_text(64)
_SI_2KB = _si_text(2048)
_SI_16KB = _si_text(16384)


SCENARIOS: list[dict] = [
    {
        "capability": "bic",
        "text": "DEUTDEFF",
        "register": _bic_register,
        "contract_factory": _bic_contract,
    },
    {
        "capability": "chemical_element",
        "text": "Fe",
        "register": _chemical_element_register,
        "contract_factory": _chemical_element_contract,
    },
    {
        "capability": "coordinates",
        "text": "48.8566, 2.3522",
        "register": _coordinates_register,
        "contract_factory": _coordinates_contract,
    },
    {
        "capability": "country",
        "text": "United States",
        "register": _country_register,
        "contract_factory": _country_contract,
    },
    {
        "capability": "credit_card",
        "text": "4111111111111111",
        "register": _credit_card_register,
        "contract_factory": _credit_card_contract,
    },
    {
        "capability": "currency",
        "text": "USD",
        "register": _currency_register,
        "contract_factory": _currency_contract,
    },
    {
        "capability": "date",
        "text": "2026-01-15",
        "register": _date_register,
        "contract_factory": _date_contract,
    },
    {
        "capability": "doi",
        "text": "10.1038/nature12345",
        "register": _doi_register,
        "contract_factory": _doi_contract,
    },
    {
        "capability": "domain",
        "text": "münchen.DE.",
        "register": _domain_register,
        "contract_factory": _domain_contract,
    },
    {
        "capability": "email",
        "text": "user@example.com",
        "register": _email_register,
        "contract_factory": _email_contract,
    },
    {
        "capability": "gtin",
        "text": "614141999996",
        "register": _gtin_register,
        "contract_factory": _gtin_contract,
    },
    {
        "capability": "iban",
        "text": "GB82WEST12345698765432",
        "register": _iban_register,
        "contract_factory": _iban_contract,
    },
    {
        "capability": "ip",
        "text": "192.168.1.1",
        "register": _ip_register,
        "contract_factory": _ip_contract,
    },
    {
        "capability": "isbn",
        "text": "9780306406157",
        "register": _isbn_register,
        "contract_factory": _isbn_contract,
    },
    {
        "capability": "isin",
        "text": "US0378331005",
        "register": _isin_register,
        "contract_factory": _isin_contract,
    },
    {
        "capability": "issn",
        "text": "0317-8471",
        "register": _issn_register,
        "contract_factory": _issn_contract,
    },
    {
        "capability": "language",
        "text": "en-US",
        "register": _language_register,
        "contract_factory": _language_contract,
    },
    {
        "capability": "lei",
        "text": "213800KUD8LAJWSQ9D15",
        "register": _lei_register,
        "contract_factory": _lei_contract,
    },
    {
        "capability": "mac_address",
        "text": "00:1A:2B:3C:4D:5E",
        "register": _mac_address_register,
        "contract_factory": _mac_address_contract,
    },
    {
        "capability": "money",
        "text": "USD 500.00",
        "register": _money_register,
        "contract_factory": _money_contract,
    },
    {
        "capability": "orcid",
        "text": "0000-0002-1825-0097",
        "register": _orcid_register,
        "contract_factory": _orcid_contract,
    },
    {
        "capability": "phone",
        "text": "+1 555 123 4567",
        "register": _phone_register,
        "contract_factory": _phone_contract,
    },
    {
        "capability": "si_unit",
        "text": "kg",
        "register": _si_unit_register,
        "contract_factory": _si_unit_contract,
    },
    {
        "capability": "timezone",
        "text": "America/New_York",
        "register": _timezone_register,
        "contract_factory": _timezone_contract,
    },
    {
        "capability": "url",
        "text": "https://example.com/path",
        "register": _url_register,
        "contract_factory": _url_contract,
    },
    {
        "capability": "utc_offset",
        "text": "+05:30",
        "register": _utc_offset_register,
        "contract_factory": _utc_offset_contract,
    },
    {
        "capability": "uuid",
        "text": "6ba7b810-9dad-11d1-80b4-00c04fd430c8",
        "register": _uuid_register,
        "contract_factory": _uuid_contract,
    },
    {
        "capability": "freeze",
        "text": "freeze",
        "register": _freeze_register,
        "contract_factory": _freeze_contract,
    },
    {
        "capability": "si_unit-recognition-64B",
        "text": _SI_64B,
        "register": _si_unit_register,
        "contract_factory": _si_unit_contract,
    },
    {
        "capability": "si_unit-recognition-2KB",
        "text": _SI_2KB,
        "register": _si_unit_register,
        "contract_factory": _si_unit_contract,
    },
    {
        "capability": "si_unit-recognition-16KB",
        "text": _SI_16KB,
        "register": _si_unit_register,
        "contract_factory": _si_unit_contract,
    },
]
