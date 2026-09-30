"""UNGM UNSPSC code-structure rules: hierarchy lanes and level padding.

Both rule classes validate the positional shape only — no authority table
is consulted. Codeset membership (including ancestor liveness) is owned by
``undp_unspsc_codeset_ed2023.Section3CodesetMembership``.
"""

from __future__ import annotations

from paxman.capabilities.UNSPSC.notation import UNSPSCNotation
from paxman.core.contract import Contract
from paxman.core.domain import Provenance, Rule, RuleStrategy

PUBLICATION = Provenance(
    authority="United Nations Development Programme",
    specification_name="UNSPSC Code Structure (UNGM Help Center)",
    kind="specification",
    reference_url="https://help.ungm.org/hc/en-us/articles/360012816160-What-are-UNSPSC-codes-",
    version="2025-07-08",
    lifecycle="active",
    publication_year=2025,
)


def _is_hierarchy_shape(notation: UNSPSCNotation) -> bool:
    """8-digit ASCII stem on a 6/8/10 spelled lane with a coherent suffix."""
    if len(notation.digits) != 8:
        return False
    if not notation.digits.isascii() or not notation.digits.isdigit():
        return False
    if notation.native_length not in (6, 8, 10):
        return False
    if notation.native_length == 10:
        return (
            len(notation.function) == 2
            and notation.function.isascii()
            and notation.function.isdigit()
        )
    return notation.function == ""


def _is_padding_consistent(notation: UNSPSCNotation) -> bool:
    """Trailing-00 pairs form a well-formed lattice (no mid-zero breaks).

    Once a ``00`` pair appears, every following pair must also be ``00``:
    ``43000000``/``43210000``/``43211500`` are well-formed, ``43001503``
    and ``00101501`` are not. (Unissued but well-formed stems such as
    ``43111503`` pass here and fail codeset membership instead.)
    """
    pairs = [notation.digits[i : i + 2] for i in (0, 2, 4, 6)]
    seen_zero = False
    for pair in pairs:
        if pair == "00":
            seen_zero = True
        elif seen_zero:
            return False
    return True


class Section1HierarchyStructure(Rule[UNSPSCNotation]):
    """UNGM structure Section 1 — hierarchy lanes (6/8/10, ASCII digits)."""

    name = "Section 1-hierarchy-structure"
    strategy = RuleStrategy.PARSER
    provenance = PUBLICATION
    citation = "Four-level hierarchy, purely numeric codes"
    target_semantics = frozenset({"unspsc_recognition"})
    requires_features = frozenset()

    def matches(self, notation: UNSPSCNotation, contract: Contract) -> bool:
        """Check whether the notation is on a valid hierarchy lane."""
        return _is_hierarchy_shape(notation)

    def normalize(self, notation: UNSPSCNotation, contract: Contract) -> str:
        """Normalize to the 8-digit compact stem."""
        return notation.digits


class Section2LevelPadding(Rule[UNSPSCNotation]):
    """UNGM structure Section 2 — 00-pair lattice consistency."""

    name = "Section 2-level-padding"
    strategy = RuleStrategy.PARSER
    provenance = PUBLICATION
    citation = "Level padding (segment 000000, family 0000, class 00)"
    target_semantics = frozenset({"unspsc_recognition"})
    requires_features = frozenset()

    def matches(self, notation: UNSPSCNotation, contract: Contract) -> bool:
        """Check whether the padding lattice is well-formed."""
        if not _is_hierarchy_shape(notation):
            return False
        return _is_padding_consistent(notation)

    def normalize(self, notation: UNSPSCNotation, contract: Contract) -> str:
        """Normalize to the 8-digit compact stem."""
        return notation.digits
