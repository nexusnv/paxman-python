"""ISBN Users' Manual 2012 rule: ISBN-10 check digit (mod-11)."""

from paxman.capabilities.ISBN.notation import ISBNNotation
from paxman.core.domain import Contract, Provenance, Rule, RuleStrategy

PUBLICATION = Provenance(
    authority="International ISBN Agency",
    specification_name="ISBN Users' Manual",
    kind="specification",
    reference_url=(
        "https://www.isbn-international.org/sites/default/files/"
        "ISBN%20Manual%202012%20-corr.pdf"
    ),
    version="2012",
    lifecycle="superseded",  # ISBN-10 removed from the current standard (memo §10.5)
    publication_year=2012,
)


def _isbn10_check_digit(chars: str) -> bool:
    """mod-11 (weights 10..2 over the first 9); final char 0-9 or X (=10)."""
    total = sum(int(c) * (10 - i) for i, c in enumerate(chars[:9]))
    check = (11 - total % 11) % 11
    return chars[9].upper() == ("X" if check == 10 else str(check))


class Section6Isbn10CheckDigit(Rule[ISBNNotation]):
    """ISBN Users' Manual - ISBN-10 check digit."""

    name = "Section 6-isbn10-check-digit"
    strategy = RuleStrategy.PARSER
    provenance = PUBLICATION
    citation = "Section 6 (ISBN-10 check digit)"
    target_semantics = frozenset({"isbn10_recognition"})
    requires_features = frozenset()

    def matches(self, notation: ISBNNotation, contract: Contract) -> bool:
        if notation.shape != "isbn10" or len(notation.digits) != 10:
            return False
        if not notation.digits.isascii():
            return False
        if not notation.digits[:9].isdigit():
            return False
        return _isbn10_check_digit(notation.digits)

    def normalize(self, notation: ISBNNotation, contract: Contract) -> str:
        """ISBN-10 -> ISBN-13: '978' + first 9 + recomputed mod-10 check digit."""
        try:
            base = "978" + notation.digits[:9]
            weighted = sum(
                int(d) * (1 if i % 2 == 0 else 3) for i, d in enumerate(base)
            )
            return base + str((10 - weighted % 10) % 10)
        except ValueError:
            return notation.digits
