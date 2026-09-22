"""GS1 Prefix allocation — Section 2 GS1 prefix membership."""

from __future__ import annotations

from paxman.capabilities.GTIN.notation import GTINNotation
from paxman.capabilities.GTIN.rules.data.gs1_prefix import (
    GS1_GTIN8_EXCEPTIONS,
    GS1_MO_RANGES,
)
from paxman.core.contract import Contract
from paxman.core.domain import Provenance, Rule, RuleStrategy

PUBLICATION = Provenance(
    authority="GS1",
    specification_name="GS1 Prefix allocation",
    kind="registry",
    reference_url="https://www.gs1.org/standards/id-keys/company-prefix",
    version="Rolling 2026",
    lifecycle="active",
    publication_year=2026,
)


def _gs1_mod10_is_valid(digits: str) -> bool:
    """GS1 Mod-10 check (local copy — never import across capabilities)."""
    if len(digits) < 2:
        return False
    total = sum(
        int(d) * (3 if i % 2 == 0 else 1) for i, d in enumerate(reversed(digits[:-1]))
    )
    return int(digits[-1]) == (10 - total % 10) % 10


def _native_view(digits: str) -> str:
    """Zero-strip maximally, subject to a remaining length in {8,12,13,14}.

    ``digits`` is the as-spelled spelling (native_length == len(digits)).
    Stripping recovers the *entity view* the prefix was assigned in — a
    padded GTIN-13 (``05901234123457``) is really prefix 590, not 059.
    When maximal stripping leaves a length outside the four GTIN lengths
    (e.g. ``01234567`` -> ``1234567``, 7 chars), fall back to as-spelled.
    """
    stripped = digits.lstrip("0")
    if len(stripped) in (8, 12, 13, 14):
        return stripped
    return digits


def _prefix_key(view: str) -> str | None:
    """Allocation key for the (possibly zero-stripped) view.

    - len 8:  GTIN-8 prefix; ``962`` spans three MOs so it resolves at
      4 chars (``GS1_GTIN8_EXCEPTIONS``), every other prefix at 3.
    - len 12: UPC-A is the EAN-13 view with a prepended zero, so key the
      EAN-13 prefix ``0 + view[:2]`` (``614...`` -> ``061``, GS1 US).
    - len 13: EAN-13 prefix ``view[:3]``.
    - len 14: GTIN-14 packaging indicator occupies position 0; the prefix
      is ``view[1:4]`` (``10614...`` -> ``061``).
    """
    n = len(view)
    if n == 8:
        return view[:4] if view[:3] == "962" else view[:3]
    if n == 12:
        return "0" + view[:2]
    if n == 13:
        return view[:3]
    if n == 14:
        return view[1:4]
    return None


def _prefix_allocated(digits: str) -> bool:
    """MO-prefix membership on the native view (never the padded view)."""
    key = _prefix_key(_native_view(digits))
    if key is None:
        return False
    if len(key) == 4:
        return key in GS1_GTIN8_EXCEPTIONS
    try:
        prefix = int(key)
    except ValueError:
        return False
    return any(s <= prefix <= e for s, e, _ in GS1_MO_RANGES)


class Section2Gs1Prefix(Rule[GTINNotation]):
    """GS1 Prefix allocation — Section 2 GS1 prefix membership."""

    name = "Section 2-gs1-prefix"
    strategy = RuleStrategy.LOOKUP_TABLE
    provenance = PUBLICATION
    citation = "Section 2 (GS1 prefix allocation)"
    target_semantics = frozenset({"gtin_recognition"})
    requires_features = frozenset()

    def matches(self, notation: GTINNotation, contract: Contract) -> bool:
        digits = notation.digits
        if not isinstance(digits, str):
            return False
        if len(digits) not in (8, 12, 13, 14):
            return False
        if notation.native_length != len(digits):
            return False
        if not digits.isascii() or not digits.isdigit():
            return False
        if not _gs1_mod10_is_valid(digits):
            return False
        return _prefix_allocated(digits)

    def normalize(self, notation: GTINNotation, contract: Contract) -> str:
        return notation.digits.rjust(14, "0")
