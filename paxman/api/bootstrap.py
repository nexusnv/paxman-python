"""Sanctioned bootstrap: register every shipped capability in one call."""

from __future__ import annotations

from typing import Any

from paxman.capabilities import (
    BIC,
    IBAN,
    IP,
    ISBN,
    ISSN,
    ORCID,
    URL,
    Coordinates,
    Country,
    Currency,
    Date,
    Email,
    Language,
    MacAddress,
    Money,
    Phone,
    SIUnit,
)
from paxman.core.capability import Capability
from paxman.core.discovery import get_capability, register_capability
from paxman.core.errors import CapabilityError

# Fixed, documented order (alphabetical by capability registry name) —
# bootstrap is deterministic. D2: literal tuple, no dynamic enumeration.
_SHIPPED: tuple[type[Capability[Any]], ...] = (
    BIC,
    Coordinates,
    Country,
    Currency,
    Date,
    Email,
    IBAN,
    IP,
    ISBN,
    ISSN,
    Language,
    MacAddress,
    Money,
    ORCID,
    Phone,
    SIUnit,
    URL,
)


def list_shipped_capabilities() -> tuple[str, ...]:
    """List shipped capability names in defined order.

    Returns:
        Tuple of capability names shipped with the library, in the
        deterministic order defined by ``_SHIPPED`` (alphabetical).
    """
    return tuple(cls.name for cls in _SHIPPED)


def register_all_shipped() -> tuple[str, ...]:
    """Register every shipped capability not already registered.

    Idempotent by name: a capability already registered (including a
    caller-registered subclass) is skipped, never overridden. Does not
    freeze the registry — freezing still happens on the first
    ``canonicalize()`` call. Raises ``CapabilityError`` if the registry is
    already frozen and anything remains to register.

    Threading contract: complete registration — single-calls or this
    helper — from a single thread before the first ``canonicalize()``
    call; post-freeze reads are safe from any thread.

    Returns:
        Names newly registered, in call order.
    """
    registered: list[str] = []
    for cls in _SHIPPED:
        try:
            get_capability(cls.name)
        except CapabilityError:
            register_capability(cls())
            registered.append(cls.name)
    return tuple(registered)
