"""MAC address notation - grammar-normalized compact hex form."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class MacAddressNotation:
    """MAC address notation - compact plus shape discriminator.

    ``compact`` is the full identifier, uppercase hex, separators stripped:
    exactly 12 hex digits (EUI-48) or 16 hex digits (EUI-64).
    ``shape`` discriminates the two identifier lengths ("eui48" / "eui64"),
    mirroring the ISBN two-length precedent.

    The grammar never validates OUI membership or interprets the U/L and I/G
    bits; rules own that (grammar/rule boundary per HOW_TO_ADD_NEW_GRAMMAR.md).
    Derived rule-side values: OUI/first block = ``compact[:6]``; U/L bit =
    ``int(compact[0:2], 16) & 0x02``; I/G bit = ``int(compact[0:2], 16) & 0x01``.
    """

    compact: str  # e.g. "001A2B3C4D5E" (12) or "001A2B3C4D5E6677" (16) - [0-9A-F]
    shape: str  # "eui48" or "eui64" - length discriminator
