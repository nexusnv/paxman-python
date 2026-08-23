"""CLDR v45 localized country name validation rule (released 2024-04-18)."""

from __future__ import annotations

from paxman.capabilities.Country.notation import CountryNotation, normalize_name
from paxman.capabilities.Country.rules.data.cldr_ed2025 import LOCALIZED_TO_ALPHA2
from paxman.core.contract import Contract
from paxman.core.domain import Provenance, Rule, RuleStrategy

# Normalized localized-name lookup view: keys normalized with the shared
# Country syntax normalizer so grammar tokens and rule lookups agree; values
# unchanged.
#
# Single-authority precedence policy: these normalized keys (e.g. "MEXICO"
# from Spanish "México") are owned by CLDR while localized matching is
# enabled. A normalized key can collide with an ISO 3166-1 English short
# name (e.g. "MEXICO" == English "Mexico"); the ISO name rule defers to this
# view when ``include_localized`` is enabled, so a localized name is never
# also validated by the ISO authority.
LOCALIZED_TO_ALPHA2_NORMALIZED: dict[str, str] = {
    normalize_name(name): alpha2 for name, alpha2 in LOCALIZED_TO_ALPHA2.items()
}

PUBLICATION = Provenance(
    authority="Unicode",
    specification_name="CLDR v45",
    kind="registry",
    reference_url="https://cldr.unicode.org/",
    version="45",
    lifecycle="active",
    publication_year=2024,
)


class SectionLocalizedNames(Rule[CountryNotation]):
    """CLDR v45 Section: localized country names (released 2024-04-18).

    Validates name shape against curated multilingual names (zh, es, fr).
    Activation is engine-owned: the engine runs this rule only when the
    contract enables ``include_localized``, via ``Rule.requires_features``.
    """

    name = "Section-localized-names"
    strategy = RuleStrategy.LOOKUP_TABLE
    provenance = PUBLICATION
    citation = "CLDR v45 localized country names"
    target_semantics = frozenset({"name_recognition"})
    requires_features = frozenset({"include_localized"})

    def matches(self, notation: CountryNotation, contract: Contract) -> bool:
        """Check if notation is a valid localized name.

        Validates notation/table membership only. Whether the rule runs at
        all is decided by the engine from ``requires_features``.

        Args:
            notation: Country notation to validate.
            contract: Contract configuration.

        Returns:
            True if notation.shape == "name" AND the normalized name is in
            the normalized LOCALIZED_TO_ALPHA2 view.
        """
        if notation.shape != "name":
            return False
        return normalize_name(notation.value) in LOCALIZED_TO_ALPHA2_NORMALIZED

    def normalize(self, notation: CountryNotation, contract: Contract) -> str:
        """Normalize to canonical alpha-2 code.

        Args:
            notation: Validated notation.
            contract: Contract configuration.

        Returns:
            Uppercase alpha-2 code.
        """
        return LOCALIZED_TO_ALPHA2_NORMALIZED[normalize_name(notation.value)]
