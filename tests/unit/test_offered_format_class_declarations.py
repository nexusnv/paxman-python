"""Offered-format class declarations — ADR-0011 classification-clause scan.

ADR-0011's classification clause requires every offered format's class to be
declared at the contract seam. This scan enforces that presence structurally:
for every shipped capability with a non-empty ``OFFERED_OUTPUT_FORMATS``, the
contract class docstring must (a) name every offered format and (b) mention
at least one ADR-0011 class term (``encoding`` / ``expansion`` /
``quantization`` / ``projection``). The scan enforces presence, not prose
quality — it is the codified review checklist a reviewer can point to;
``HOW_TO_ADD_NEW_CAPABILITY.md`` (offered-formats step) tells contributors
what to write.

Projections are never offered. A surviving waived projection (Language
``alpha3`` / ``alpha3-bib`` / ``name`` per the ADR-0011 Consequences
amendment) is a recorded waiver, and the term scan accepts its word.
"""

from __future__ import annotations

import inspect

import pytest

from paxman.api.bootstrap import list_shipped_capabilities
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
    Element,
    Email,
    Language,
    MacAddress,
    Money,
    Phone,
    SIUnit,
)

pytestmark = pytest.mark.unit

# Name -> shipped capability class (keyed by the registry names the
# bootstrap list reports).
_FACTORIES = {
    "bic": BIC,
    "coordinates": Coordinates,
    "country": Country,
    "currency": Currency,
    "date": Date,
    "email": Email,
    "iban": IBAN,
    "ip": IP,
    "isbn": ISBN,
    "issn": ISSN,
    "language": Language,
    "mac_address": MacAddress,
    "money": Money,
    "orcid": ORCID,
    "phone": Phone,
    "element": Element,
    "si_unit": SIUnit,
    "url": URL,
}

_CLASS_TERMS: tuple[str, ...] = ("encoding", "expansion", "quantization", "projection")


def test_factory_map_covers_shipped_capabilities() -> None:
    """Structural gate: the scan's factory map is the shipped capability list."""
    assert set(_FACTORIES) == set(list_shipped_capabilities()), (
        "the class-declaration scan must cover exactly the shipped capabilities"
    )


def test_offered_format_classes_are_declared() -> None:
    """Every offered format is named in the contract docstring with a class term.

    ADR-0011 classification clause: every offered format belongs to exactly
    one class — encoding, same-entity expansion, or documented quantization
    — declared in the contract docstring. A capability with no offered
    formats is scanned vacuously (single-format capabilities cannot violate
    the invariant).
    """
    offenders: list[str] = []
    for name in sorted(_FACTORIES):
        contract_cls = type(_FACTORIES[name].create_contract())
        offered = sorted(contract_cls.OFFERED_OUTPUT_FORMATS)
        if not offered:
            continue
        doc = inspect.getdoc(contract_cls) or ""
        missing = [fmt for fmt in offered if fmt not in doc]
        terms = [term for term in _CLASS_TERMS if term in doc]
        if missing or not terms:
            offenders.append(
                f"{name} ({contract_cls.__name__}): "
                f"formats_missing_from_docstring={missing}, "
                f"class_terms_found={terms}"
            )
    assert offenders == [], (
        "ADR-0011 classification clause: every offered format must be "
        "declared in its contract class docstring, with at least one class "
        "term (encoding/expansion/quantization/projection). Offenders:\n"
        + "\n".join(offenders)
    )
