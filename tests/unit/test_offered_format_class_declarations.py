"""Offered-format class declarations — ADR-0011 classification-clause scan.

ADR-0011's classification clause requires every offered format's class to be
declared at the contract seam. This scan enforces that presence structurally:
for every shipped capability with a non-empty ``OFFERED_OUTPUT_FORMATS``,
every offered format must be associated with exactly one ADR-0011 class term
(``encoding`` / ``expansion`` / ``quantization`` / ``projection``) in the
contract class docstring — association means a shared paragraph (blank-line
delimited) naming both the format and the term, so a class word elsewhere in
the docstring cannot cover an undeclared format. The scan enforces presence,
not prose quality — it is the codified review checklist a reviewer can point
to; ``HOW_TO_ADD_NEW_CAPABILITY.md`` (offered-formats step) tells
contributors what to write.

Projections are never offered. The ``projection`` term is permitted only in
the Language contract (the recorded waiver set: ``alpha3`` / ``alpha3-bib`` /
``name`` per the ADR-0011 Consequences amendment); any other contract
mentioning it — even for a removed format — must reword to a non-class term.
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
    """Every offered format is associated with exactly one class term.

    ADR-0011 classification clause: every offered format belongs to exactly
    one class — encoding, same-entity expansion, or documented quantization
    — declared in the contract docstring. Association is per paragraph
    (blank-line delimited): a paragraph naming the format must also name its
    class term. A capability with no offered formats is scanned vacuously
    (single-format capabilities cannot violate the invariant).
    """
    offenders: list[str] = []
    for name in sorted(_FACTORIES):
        contract_cls = type(_FACTORIES[name].create_contract())
        offered = sorted(contract_cls.OFFERED_OUTPUT_FORMATS)
        if not offered:
            continue
        doc = inspect.getdoc(contract_cls) or ""
        paragraphs = doc.split("\n\n")
        unassociated = [
            fmt
            for fmt in offered
            if not any(
                fmt in para and any(term in para for term in _CLASS_TERMS)
                for para in paragraphs
            )
        ]
        stray_projection = (
            "projection" in doc and contract_cls.capability_name != "language"
        )
        if unassociated or stray_projection:
            offenders.append(
                f"{name} ({contract_cls.__name__}): "
                f"formats_without_class={unassociated}, "
                f"stray_projection_term={stray_projection}"
            )
    assert offenders == [], (
        "ADR-0011 classification clause: every offered format must share a "
        "docstring paragraph with its class term "
        "(encoding/expansion/quantization/projection), and only the Language "
        "contract may mention projections (recorded waiver set). Offenders:\n"
        + "\n".join(offenders)
    )
