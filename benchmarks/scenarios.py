"""Benchmark scenarios — one deterministic input per capability (Item 7).

Inputs chosen to exercise the hot path: recognition + validation + formatting.
No network, no clock, no randomness — deterministic per library snapshot.
"""

from __future__ import annotations


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
        "capability": "country",
        "text": "United States",
        "register": _country_register,
        "contract_factory": _country_contract,
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
        "capability": "email",
        "text": "user@example.com",
        "register": _email_register,
        "contract_factory": _email_contract,
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
        "capability": "money",
        "text": "USD 500.00",
        "register": _money_register,
        "contract_factory": _money_contract,
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
        "capability": "url",
        "text": "https://example.com/path",
        "register": _url_register,
        "contract_factory": _url_contract,
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
