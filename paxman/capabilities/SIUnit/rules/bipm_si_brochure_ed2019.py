"""BIPM SI Brochure rules (9th edition, 2019).

The SI Brochure defines the base units (Table 1), derived units with
special names (Tables 3–4), non-SI units accepted for use with the SI
(Table 8 and §4.2), and the prefix symbols (Table 5). Each section validates
the corresponding symbol shape against its authority table. Syntax-only
recognition is the grammars' job; the rules resolve the canonical
symbol and provide provenance.
"""

from __future__ import annotations

from paxman.capabilities.SIUnit.notation import SIUnitNotation
from paxman.capabilities.SIUnit.rules.data.prefixed_unit_names import (
    PREFIXED_NAME_TO_SYMBOL,
)
from paxman.capabilities.SIUnit.rules.data.prefixed_units import PREFIXED_UNIT_SYMBOLS
from paxman.capabilities.SIUnit.rules.data.si_base_units import BASE_UNIT_SYMBOLS
from paxman.capabilities.SIUnit.rules.data.si_derived_units import DERIVED_UNIT_SYMBOLS
from paxman.capabilities.SIUnit.rules.data.si_nonsi_units import (
    LITRE_WRITTEN_FORMS,
    NONSI_UNIT_SYMBOLS,
)
from paxman.capabilities.SIUnit.rules.data.unit_names import NAME_TO_SYMBOL
from paxman.core.contract import Contract
from paxman.core.domain import Provenance, Rule, RuleStrategy

# Full name→symbol resolution: maintained official names + generated
# prefixed names (ADR §14). No key overlap by construction.
FULL_NAME_TO_SYMBOL = NAME_TO_SYMBOL | PREFIXED_NAME_TO_SYMBOL

PUBLICATION = Provenance(
    authority="BIPM",
    specification_name="SI Brochure: The International System of Units (SI)",
    kind="specification",
    reference_url="https://www.bipm.org/en/publications/si-brochure",
    version="9th edition",
    lifecycle="active",
    publication_year=2019,
)


class SectionBaseUnits(Rule[SIUnitNotation]):
    """SI Brochure Table 1 — base unit symbols."""

    name = "Section 2.3.1-base-units"
    strategy = RuleStrategy.LOOKUP_TABLE
    provenance = PUBLICATION
    citation = "BIPM SI Brochure (9th ed., 2019), Table 1"
    target_semantics = frozenset({"symbol_recognition"})
    requires_features = frozenset()

    def matches(self, notation: SIUnitNotation, contract: Contract) -> bool:
        """Check if the notation is a base-unit symbol."""
        if (
            contract.year is not None
            and contract.year < self.provenance.publication_year
        ):
            return False
        if notation.shape != "symbol":
            return False
        return notation.text in BASE_UNIT_SYMBOLS

    def normalize(self, notation: SIUnitNotation, contract: Contract) -> str:
        """Normalize to the canonical base-unit symbol."""
        return notation.text


class SectionDerivedUnits(Rule[SIUnitNotation]):
    """SI Brochure Tables 3–4 — derived units with special names."""

    name = "Section 2.3.2-derived-units"
    strategy = RuleStrategy.LOOKUP_TABLE
    provenance = PUBLICATION
    citation = "BIPM SI Brochure (9th ed., 2019), Tables 3–4"
    target_semantics = frozenset({"symbol_recognition"})
    requires_features = frozenset()

    def matches(self, notation: SIUnitNotation, contract: Contract) -> bool:
        """Check if the notation is a derived-unit symbol."""
        if (
            contract.year is not None
            and contract.year < self.provenance.publication_year
        ):
            return False
        if notation.shape != "symbol":
            return False
        return notation.text in DERIVED_UNIT_SYMBOLS

    def normalize(self, notation: SIUnitNotation, contract: Contract) -> str:
        """Normalize to the canonical derived-unit symbol."""
        return notation.text


class SectionNonSiUnits(Rule[SIUnitNotation]):
    """SI Brochure Tables 8–9 — non-SI units accepted for use with the SI.

    "l" (litre) canonicalizes to "L" (D3). "′" and "″" are recognized
    but normalize to themselves.
    """

    name = "Section 4.1-non-si-units"
    strategy = RuleStrategy.LOOKUP_TABLE
    provenance = PUBLICATION
    citation = "BIPM SI Brochure (9th ed., 2019), Tables 8–9"
    target_semantics = frozenset({"symbol_recognition"})
    requires_features = frozenset()

    def matches(self, notation: SIUnitNotation, contract: Contract) -> bool:
        """Check if the notation is a non-SI unit symbol."""
        if (
            contract.year is not None
            and contract.year < self.provenance.publication_year
        ):
            return False
        if notation.shape != "symbol":
            return False
        return notation.text in NONSI_UNIT_SYMBOLS

    def normalize(self, notation: SIUnitNotation, contract: Contract) -> str:
        """Normalize to the canonical symbol ("l" -> "L")."""
        if notation.text in LITRE_WRITTEN_FORMS:
            return "L"
        return notation.text


class SectionPrefixes(Rule[SIUnitNotation]):
    """SI Brochure Table 5 + §3.2 — prefixed unit symbols.

    A prefixed symbol ("km", "MHz", "µg") is a valid unit: prefix symbol
    concatenated with a prefixable unit symbol, generated from the
    maintained tables (Task 4). A bare prefix symbol ("k", "da") is not
    a unit and never matches — it stays INVALID (recognized, unresolved).
    """

    name = "Section 3.2-prefixes"
    strategy = RuleStrategy.LOOKUP_TABLE
    provenance = PUBLICATION
    citation = "BIPM SI Brochure (9th ed., 2019), Table 5 and §3.2"
    target_semantics = frozenset({"symbol_recognition"})
    requires_features = frozenset()

    def matches(self, notation: SIUnitNotation, contract: Contract) -> bool:
        """Check if the notation is a prefixed unit symbol."""
        if (
            contract.year is not None
            and contract.year < self.provenance.publication_year
        ):
            return False
        if notation.shape != "symbol":
            return False
        return notation.text in PREFIXED_UNIT_SYMBOLS

    def normalize(self, notation: SIUnitNotation, contract: Contract) -> str:
        """Normalize to the canonical prefixed symbol."""
        return notation.text


class SectionNames(Rule[SIUnitNotation]):
    """SI Brochure Tables 1, 3–4, 8–9 — unit names resolve to symbols.

    The name grammar case-folds (ADR §6 D4), so this lookup is exact. The table is
    FULL_NAME_TO_SYMBOL (maintained official names + generated prefixed
    names, ADR §14): "megahertz" -> "MHz", "kilometre" -> "km", "microgram" -> "µg".
    """

    name = "Section-names"
    strategy = RuleStrategy.LOOKUP_TABLE
    provenance = PUBLICATION
    citation = "BIPM SI Brochure (9th ed., 2019), Tables 1, 3–4, 8–9 (unit names)"
    target_semantics = frozenset({"name_recognition"})
    requires_features = frozenset()

    def matches(self, notation: SIUnitNotation, contract: Contract) -> bool:
        """Check if the notation is a known unit name."""
        if (
            contract.year is not None
            and contract.year < self.provenance.publication_year
        ):
            return False
        if notation.shape != "name":
            return False
        return notation.text in FULL_NAME_TO_SYMBOL

    def normalize(self, notation: SIUnitNotation, contract: Contract) -> str:
        """Normalize to the canonical unit symbol."""
        return FULL_NAME_TO_SYMBOL[notation.text]
