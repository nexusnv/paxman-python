"""Element notation — grammar-normalized token plus shape discriminator."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ElementNotation:
    """Element notation — token plus shape discriminator.

    ``token`` carries the grammar-normalized designation: ``symbol`` tokens
    use IUPAC case (``Fe``), ``name`` tokens are lowercase (``iron``), and
    ``atomic_number`` tokens are bare digits (``26``). ``shape`` is a free
    ``str`` routing key (``symbol`` | ``name`` | ``atomic_number``) that the
    rules use to select the validating authority table.
    """

    token: str  # e.g. "Fe" (symbol), "iron" (name), "26" (atomic number)
    shape: str  # "symbol" | "name" | "atomic_number" - routing key
