"""UNECE business-function rule: optional 2-digit suffix, informative only.

Any ``00``–``99`` suffix value passes when this rule runs; the suffix is
a routing hint, not validity. No value table is cited (the UNECE PDF
direct fetch is access-gated; retail/wholesale corroboration is
secondary). Gating is engine-side via ``requires_features``: with
``include_business_function=False`` the rule drops and 10-digit inputs
resolve INVALID, never MISSING.
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
    """10-digit lane carries a 2-digit suffix; shorter lanes are vacuous."""
    if notation.native_length != 10:
        return True
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
