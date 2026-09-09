#!/usr/bin/env python3
"""Generate README capability table from shipped capabilities.

Usage:
    uv run python tools/generate_readme_table.py

Prints a Markdown table to stdout derived from ``paxman/api/bootstrap.py:_SHIPPED``
and each capability's ``get_grammars()`` / ``get_rules()``. The hardcoded
``_DESCRIPTIONS`` map is the only place descriptions live outside README;
future work can move specs into capability metadata. Standard library only
plus ``paxman`` imports.

Source snapshot: ``paxman/api/bootstrap.py:_SHIPPED`` (alphabetical by
registry name) and ``paxman/capabilities/<Name>/capability.py`` grammars/rules.
Regenerate with: uv run python tools/generate_readme_table.py
"""

from __future__ import annotations

from typing import Any

from paxman.api.bootstrap import _SHIPPED  # pyright: ignore[reportPrivateUsage]
from paxman.core.domain import Grammar

# Domain + spec per capability (registry name -> (domain, description)).
# Hardcoded here and in README; keep in sync until metadata owns it.
_DESCRIPTIONS: dict[str, tuple[str, str]] = {
    "bic": (
        "Business identifier codes",
        "ISO 9362:2022, ISO 3166-1 (country codes plus XK)",
    ),
    "coordinates": ("WGS 84 coordinates", "ISO 6709:2022, RFC 5870, RFC 7946"),
    "country": ("Country codes/names", "ISO 3166, CLDR"),
    "currency": ("Currency identifiers", "ISO 4217, CLDR"),
    "date": (
        "Dates",
        "ISO 8601-1:2019 §5.2.1.1, derived conventions (US/European locale)",
    ),
    "email": ("Email addresses", "RFC 5322, RFC 6761"),
    "element": (
        "Chemical elements",
        "IUPAC Red Book 2005, IUPAC Periodic Table 04 May 2022",
    ),
    "iban": ("Bank account numbers", "ISO 13616, SWIFT Registry, MOD 97-10"),
    "ip": ("IP addresses", "RFC 791, RFC 5952"),
    "isbn": ("ISBNs", "ISO 2108, ISBN Users' Manual, ISBN Range Message"),
    "issn": ("Serial identifiers", "ISO 3297:2022"),
    "language": (
        "Language identifiers",
        "ISO 639, IANA Language Subtag Registry, BCP 47 RFC 5646, CLDR",
    ),
    "mac_address": ("MAC addresses", "IEEE Std 802-2024"),
    "money": ("Money amounts", "ISO 4217, CLDR"),
    "orcid": ("Researcher identifiers", "ISO 27729:2024, MOD 11-2"),
    "phone": ("Phone numbers", "ITU-T E.164, RFC 3966, NANP"),
    "si_unit": ("SI unit expressions", "BIPM SI Brochure, ISO 80000-1"),
    "url": ("URLs", "WHATWG URL Standard"),
}

_DISPLAY_NAMES: dict[str, str] = {
    "bic": "BIC",
    "coordinates": "Coordinates",
    "country": "Country",
    "currency": "Currency",
    "date": "Date",
    "email": "Email",
    "element": "Element",
    "iban": "IBAN",
    "ip": "IP",
    "isbn": "ISBN",
    "issn": "ISSN",
    "language": "Language",
    "mac_address": "MacAddress",
    "money": "Money",
    "orcid": "ORCID",
    "phone": "Phone",
    "si_unit": "SI Unit",
    "url": "URL",
}


def _grammar_display_names(grammars: list[Grammar[Any]]) -> list[str]:
    """Return display names by stripping ``_recognition`` suffix when present."""
    names: list[str] = []
    for grammar in grammars:
        raw = grammar.name
        if raw.endswith("_recognition"):
            raw = raw[: -len("_recognition")]
        names.append(raw)
    return names


def generate_table() -> str:
    """Return the Markdown capability table and note."""
    header = "| Capability | Domain | Grammars | Rules | Description |"
    separator = "|---|---|---|---|---|"
    lines: list[str] = [header, separator]
    for cls in _SHIPPED:
        cap = cls()
        grammars = cap.get_grammars()
        rules = cap.get_rules()
        registry_name: str = cap.name
        display = _DISPLAY_NAMES.get(registry_name, registry_name)
        domain, description = _DESCRIPTIONS[registry_name]
        grammar_names = _grammar_display_names(grammars)
        grammar_cell = f"{len(grammars)} ({', '.join(grammar_names)})"
        lines.append(
            f"| **{display}** | {domain} | {grammar_cell} |"
            f" {len(rules)} | {description} |"
        )
    note = (
        "> **Note:** Table generated from `paxman/api/bootstrap.py:_SHIPPED`"
        " (alphabetical by registry name). To regenerate, run"
        " `uv run python tools/generate_readme_table.py`."
    )
    return "\n".join(lines) + "\n\n" + note + "\n"


def main() -> None:
    print(generate_table(), end="")


if __name__ == "__main__":
    main()
