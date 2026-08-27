"""IBAN notation — grammar-normalized compact form."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class IBANNotation:
    """IBAN notation — compact + structured decomposition.

    Frozen, slots, hashable. Grammar normalizes raw input to this form;
    rules own validation (mod97, per-country length, CC allowlist).

    ``country_code`` 2-letter ISO 3166-1 alpha-2, uppercased, must be in
      SWIFT IBAN Registry (111 codes as of R99/R100 May 2026).
    ``check_digits`` 2-digit string at positions 3-4, 02-98 valid
      (00/01/99 never pass mod97).
    ``bban`` 1-30 alphanum, uppercased, spaces stripped — country-specific
      structure; generic length check is 15-34, per-country fixed length
      (e.g. DE22, NO15) enforced by rule before mod97.
    ``compact`` electronic string country_code+check_digits+bban (15-34),
      e.g. ``DE89370400440532013000``. The grammar never computes mod-97
      or per-country length; rules own them (deterministic, provenance-first).

    The ``compact`` field is the canonical electronic form; ``format_value``
    renders ``paper`` as groups-of-four. Single-value capability — two
    distinct IBANs in one input raise MultipleMentionsError.
    """

    country_code: str  # e.g. "DE" — length 2, A-Z, SWIFT-registered
    check_digits: str  # e.g. "89" — length 2, 0-9, 02-98
    bban: str  # e.g. "370400440532013000" — 1-30 alphanum, country-specific
    compact: str  # e.g. "DE89370400440532013000" — 15-34, per-country fixed
