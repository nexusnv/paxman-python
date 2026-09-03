"""ISO 3297:2022 rule: ISSN structure + mod-11 check digit.

Implements ISO 3297:2022 (7th edition 2022-06, ISSN International Centre,
Paris; supersedes 2020/2017/2007) Section 4 — 8-char ``XXXX-XXXX`` structure
(first 7 chars digits, final char digit or ``X``=10) and mod-11 weights
``8,7,6,5,4,3,2`` check digit ``check = (11 - total%%11)%%11`` with
``10→X``, ``11→0``. Case folding ``x→X`` is syntax (grammar); ``X=10`` is
semantics (this rule). ``PUBLICATION.publication_year=2022`` so
``contract(year=2021)`` → ``INVALID`` per engine year filtering (temporal
filtering — stable algorithm but edition-gated). ``ISSN-L``/``ISSN-H``
labels are lexical, not semantic (same check, coalesced semantics id).
"""

from paxman.capabilities.ISSN.notation import ISSNNotation
from paxman.core.contract import Contract
from paxman.core.domain import Provenance, Rule, RuleStrategy

PUBLICATION = Provenance(
    authority="ISSN International Centre",
    specification_name="ISO 3297:2022",
    kind="specification",
    reference_url="https://www.iso.org/standard/84536.html",
    version="2022",
    lifecycle="active",
    publication_year=2022,
)


def _issn_check(digits: str) -> str:
    """Compute expected check char for 8-char digits (weights 8→2, X=10)."""
    total = sum(int(d) * (8 - i) for i, d in enumerate(digits[:7]))
    check = (11 - total % 11) % 11
    return "X" if check == 10 else str(check)


class Section4CheckDigit(Rule[ISSNNotation]):
    """ISO 3297 Section 4 — ISSN check digit (8→2, X=10).

    Validates ``ISSNNotation.digits`` (8 chars) per ISO 3297:2022 §4:
    ``len==8``, ``digits[:7].isascii() and isdigit()``, ``digits[7]`` in
    ``0-9X``, then ``last == _issn_check(digits)`` (mod-11 weights 8→2).
    ``_issn_check`` computes ``total = sum(int(d)*(8-i) for i,d in
    enumerate(digits[:7]))`` and ``check = (11 - total%%11)%%11``. ``normalize``
    returns hyphenated ``XXXX-XXXX`` uppercased (presentation via
    ``ISSNCapability.format_value`` for ``compact``/``urn``).
    """

    name = "Section 4-issn-check-digit"
    strategy = RuleStrategy.PARSER
    provenance = PUBLICATION
    citation = "Section 4 (check digit)"
    target_semantics = frozenset({"issn_recognition"})
    requires_features = frozenset()

    def matches(self, notation: ISSNNotation, contract: Contract) -> bool:
        if len(notation.digits) != 8:
            return False
        if not notation.digits[:7].isascii() or not notation.digits[:7].isdigit():
            return False
        last = notation.digits[7].upper()
        if last not in "0123456789X":
            return False
        return last == _issn_check(notation.digits)

    def normalize(self, notation: ISSNNotation, contract: Contract) -> str:
        digits = notation.digits.upper()
        return f"{digits[:4]}-{digits[4:]}"
