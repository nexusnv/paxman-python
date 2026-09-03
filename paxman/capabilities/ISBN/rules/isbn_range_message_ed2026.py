"""ISBN Range Message rule: registrant-range issued-ness (LOOKUP_TABLE)."""

from paxman.capabilities.ISBN.notation import ISBNNotation
from paxman.capabilities.ISBN.rules.data.range_message import (
    EAN_PREFIX_RULES,
    GROUP_RULES,
)
from paxman.capabilities.ISBN.rules.data.range_message import (
    find_registrant_length as _find_length,
)
from paxman.core.domain import Contract, Provenance, Rule, RuleStrategy

PUBLICATION = Provenance(
    authority="International ISBN Agency",
    specification_name="ISBN Range Message",
    kind="registry",
    reference_url="https://www.isbn-international.org/range_file_generation",
    version="2026-08-05",
    lifecycle="active",
    publication_year=2026,
)


class Section4RegistrantRange(Rule[ISBNNotation]):
    """ISBN Range Message - registrant range issued-ness (memo §4.3 algorithm)."""

    name = "Section 4-registrant-range"
    strategy = RuleStrategy.LOOKUP_TABLE
    provenance = PUBLICATION
    citation = "Section 4 (registrant range)"
    target_semantics = frozenset({"isbn13_recognition", "isbn10_recognition"})
    requires_features = frozenset({"include_range_validation"})

    def matches(self, notation: ISBNNotation, contract: Contract) -> bool:
        digits = self._to_isbn13(notation)
        if digits is None:
            return False
        prefix = digits[:3]
        if prefix not in EAN_PREFIX_RULES:
            return False
        rest = digits[3:]
        group_len = _find_length(EAN_PREFIX_RULES[prefix], rest)
        if group_len is None:
            return False
        group = rest[:group_len]
        registrant_rules = GROUP_RULES.get(f"{prefix}-{group}")
        if registrant_rules is None:
            return False
        return _find_length(registrant_rules, rest[group_len:]) is not None

    def normalize(self, notation: ISBNNotation, contract: Contract) -> str:
        digits = self._to_isbn13(notation)
        if digits is None:
            return notation.digits
        return digits

    @staticmethod
    def _to_isbn13(notation: ISBNNotation) -> str | None:
        if notation.shape == "isbn13":
            return notation.digits
        if notation.shape == "isbn10" and len(notation.digits) == 10:
            if not notation.digits[:9].isdigit():
                return None
            base = "978" + notation.digits[:9]
            try:
                weighted = sum(
                    int(d) * (1 if i % 2 == 0 else 3) for i, d in enumerate(base)
                )
            except ValueError:
                return None
            return base + str((10 - weighted % 10) % 10)
        return None
