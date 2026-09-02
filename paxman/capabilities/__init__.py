"""Paxman capabilities — PEP 562 lazy exports (Item 8, W4).

Importing `paxman.capabilities` does not import any capability package.
`from paxman.capabilities import Email` imports only `paxman.capabilities.Email`.
This keeps `register_capability(Email())` cheap when only one capability is used.
The committed 15K-line URL IDNA table is not loaded unless URL is imported.
"""

from __future__ import annotations

import sys as _sys
from types import ModuleType as _ModuleType
from typing import TYPE_CHECKING, Any

__all__ = [
    "BIC",
    "Coordinates",
    "Country",
    "Currency",
    "Date",
    "Email",
    "IBAN",
    "IP",
    "ISBN",
    "ISSN",
    "Language",
    "MacAddress",
    "Money",
    "ORCID",
    "Phone",
    "SIUnit",
    "URL",
]

_LAZY: dict[str, tuple[str, str]] = {
    "BIC": ("paxman.capabilities.BIC.capability", "BICCapability"),
    "Coordinates": (
        "paxman.capabilities.Coordinates.capability",
        "CoordinatesCapability",
    ),
    "Country": ("paxman.capabilities.Country.capability", "CountryCapability"),
    "Currency": ("paxman.capabilities.Currency.capability", "CurrencyCapability"),
    "Date": ("paxman.capabilities.Date.capability", "DateCapability"),
    "Email": ("paxman.capabilities.Email.capability", "EmailCapability"),
    "IBAN": ("paxman.capabilities.IBAN.capability", "IBANCapability"),
    "IP": ("paxman.capabilities.IP.capability", "IPCapability"),
    "ISBN": ("paxman.capabilities.ISBN.capability", "ISBNCapability"),
    "ISSN": ("paxman.capabilities.ISSN.capability", "ISSNCapability"),
    "Language": ("paxman.capabilities.Language.capability", "LanguageCapability"),
    "MacAddress": ("paxman.capabilities.MacAddress.capability", "MacAddressCapability"),
    "Money": ("paxman.capabilities.Money.capability", "MoneyCapability"),
    "ORCID": ("paxman.capabilities.ORCID.capability", "ORCIDCapability"),
    "Phone": ("paxman.capabilities.Phone.capability", "PhoneCapability"),
    "SIUnit": ("paxman.capabilities.SIUnit.capability", "SIUnitCapability"),
    "URL": ("paxman.capabilities.URL.capability", "URLCapability"),
}

if TYPE_CHECKING:
    from paxman.capabilities.BIC.capability import BICCapability as BIC
    from paxman.capabilities.Coordinates.capability import (
        CoordinatesCapability as Coordinates,
    )
    from paxman.capabilities.Country.capability import CountryCapability as Country
    from paxman.capabilities.Currency.capability import CurrencyCapability as Currency
    from paxman.capabilities.Date.capability import DateCapability as Date
    from paxman.capabilities.Email.capability import EmailCapability as Email
    from paxman.capabilities.IBAN.capability import IBANCapability as IBAN
    from paxman.capabilities.IP.capability import IPCapability as IP
    from paxman.capabilities.ISBN.capability import ISBNCapability as ISBN
    from paxman.capabilities.ISSN.capability import ISSNCapability as ISSN
    from paxman.capabilities.Language.capability import LanguageCapability as Language
    from paxman.capabilities.MacAddress.capability import (
        MacAddressCapability as MacAddress,
    )
    from paxman.capabilities.Money.capability import MoneyCapability as Money
    from paxman.capabilities.ORCID.capability import ORCIDCapability as ORCID
    from paxman.capabilities.Phone.capability import PhoneCapability as Phone
    from paxman.capabilities.SIUnit.capability import SIUnitCapability as SIUnit
    from paxman.capabilities.URL.capability import URLCapability as URL


def __getattr__(name: str) -> Any:
    if name in _LAZY:
        import importlib

        mod_name, attr = _LAZY[name]
        mod = importlib.import_module(mod_name)
        val = getattr(mod, attr)
        globals()[name] = val
        return val
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def __dir__() -> list[str]:
    return sorted(__all__)


# PEP 562 lazy shadowing fix: submodule imports create a package entry
# shadowing the cached lazy class; fix via custom module class.


class _CapabilitiesModule(_ModuleType):
    def __getattribute__(self, name: str) -> Any:
        if name in _LAZY:
            try:
                val = super().__getattribute__(name)
                if hasattr(val, "__path__"):
                    import importlib as _importlib  # pragma: no cover

                    # pragma: no cover
                    mod_name, attr = _LAZY[name]  # pragma: no cover
                    mod = _importlib.import_module(mod_name)  # pragma: no cover
                    val = getattr(mod, attr)  # pragma: no cover
                    super().__setattr__(name, val)  # pragma: no cover
                    return val  # pragma: no cover
                return val
            except AttributeError:  # pragma: no cover
                pass  # pragma: no cover
        return super().__getattribute__(name)


_sys.modules[__name__].__class__ = _CapabilitiesModule

# Clean any already-shadowed entries left from earlier submodule imports
for _n in list(_LAZY.keys()):
    if _n in globals() and hasattr(globals()[_n], "__path__"):
        del globals()[_n]  # pragma: no cover
