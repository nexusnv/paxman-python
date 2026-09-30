"""UNECE business-function rule: the 10-digit suffix lane, informative only.

The rule speaks ONLY to the 10-digit lane: any ``00``–``99`` suffix value
passes, and shorter lanes abstain (False) so no UNECE provenance attaches
to suffix-less inputs and a pinned-Section-4 contract cannot validate
garbage (GTIN/ISNI full-conjunction precedent). Gating is engine-side via
``requires_features``: with ``include_business_function=False`` the rule
drops and the stem still validates via Sections 1–3, so the verdict stays
SUCCESS with the suffix candidate removed (ISBN corroborating-rule
precedent). Residual: ``year`` filtering that drops the 2025/2026 rules
leaves this 2005 PARSER standing alone on 10-digit shape (ADR-0012
vacuity) — disclosed, not closed.
"""

from __future__ import annotations

from paxman.capabilities.UNSPSC.notation import UNSPSCNotation
from paxman.core.contract import Contract
from paxman.core.domain import Provenance, Rule, RuleStrategy

PUBLICATION = Provenance(
    authority="United Nations Economic Commission for Europe",
    specification_name="Classification Guidelines (Business Function Identifiers)",
    kind="specification",
    reference_url=(
        "https://unece.org/fileadmin/DAM/trade/agr/meetings/ge.11/2005/2005_i04_UNSPSC.pdf"
    ),
    version="v2.04",
    lifecycle="active",
    publication_year=2005,
)


def _is_suffix_coherent(notation: UNSPSCNotation) -> bool:
    """10-digit lane carries a well-formed 2-digit suffix; other lanes abstain."""
    if notation.native_length != 10:
        return False
    function = notation.function
    return len(function) == 2 and function.isascii() and function.isdigit()


class Section4BusinessFunctionSuffix(Rule[UNSPSCNotation]):
    """UNECE guidelines Section 4 — business-function suffix (gated)."""

    name = "Section 4-business-function-suffix"
    strategy = RuleStrategy.PARSER
    provenance = PUBLICATION
    citation = "Business Function Identifiers (optional 2-digit suffix)"
    target_semantics = frozenset({"unspsc_recognition"})
    requires_features = frozenset({"include_business_function"})

    def matches(self, notation: UNSPSCNotation, contract: Contract) -> bool:
        """Check whether the suffix lane is coherent (any value passes)."""
        return _is_suffix_coherent(notation)

    def normalize(self, notation: UNSPSCNotation, contract: Contract) -> str:
        """Normalize to the 8-digit compact stem."""
        return notation.digits
