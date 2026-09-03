"""ISO 2108:2017 rules: ISBN-13 check digit and GS1 prefix."""

from paxman.capabilities.ISBN.notation import ISBNNotation
from paxman.core.domain import Contract, Provenance, Rule, RuleStrategy

PUBLICATION = Provenance(
    authority="ISO",
    specification_name="ISO 2108:2017",
    kind="specification",
    reference_url="https://www.iso.org/standard/65483.html",
    version="2017",
    lifecycle="active",
    publication_year=2017,
)

_GS1_PREFIXES = frozenset({"978", "979"})


def _isbn13_check_digit(digits: str) -> bool:
    """mod-10 over the first 12 digits (weights 1, 3); check = (10 - S % 10) % 10."""
    weighted = sum(int(d) * (1 if i % 2 == 0 else 3) for i, d in enumerate(digits[:12]))
    return int(digits[12]) == (10 - weighted % 10) % 10


class Section53Isbn13CheckDigit(Rule[ISBNNotation]):
    """ISO 2108 Section 5.3 - ISBN-13 check digit (structure + prefix)."""

    name = "Section 5.3-isbn13-check-digit"
    strategy = RuleStrategy.PARSER
    provenance = PUBLICATION
    citation = "Section 5.3 (ISBN-13 check digit)"
    target_semantics = frozenset({"isbn13_recognition"})
    requires_features = frozenset()

    def matches(self, notation: ISBNNotation, contract: Contract) -> bool:
        if notation.shape != "isbn13" or len(notation.digits) != 13:
            return False
        if not notation.digits.isascii():
            return False
        if notation.digits[:3] not in _GS1_PREFIXES:  # ISO 2108 §4.2 structure
            return False
        return _isbn13_check_digit(notation.digits)

    def normalize(self, notation: ISBNNotation, contract: Contract) -> str:
        return notation.digits


class Section42Gs1Prefix(Rule[ISBNNotation]):
    """ISO 2108 Section 4.2 - GS1 prefix is 978 or 979.

    Note: §4.2 defines the GS1 prefix set, but operationally this rule also
    verifies the §5.3 check digit so that both ISO 2108 provenances (prefix
    + check digit) are independently attributable. The duplicate check is
    intentional — see audit B3.
    """

    name = "Section 4.2-gs1-prefix"
    strategy = RuleStrategy.LOOKUP_TABLE
    provenance = PUBLICATION
    citation = "Section 4.2 (GS1 prefix)"
    target_semantics = frozenset({"isbn13_recognition"})
    requires_features = frozenset()

    def matches(self, notation: ISBNNotation, contract: Contract) -> bool:
        if notation.shape != "isbn13" or len(notation.digits) != 13:
            return False
        if notation.digits[:3] not in _GS1_PREFIXES:
            return False
        return _isbn13_check_digit(notation.digits)

    def normalize(self, notation: ISBNNotation, contract: Contract) -> str:
        return notation.digits
