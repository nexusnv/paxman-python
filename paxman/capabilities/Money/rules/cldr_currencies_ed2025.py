"""Unicode CLDR currency rules: currency symbols and display names.

Currency symbols and display names share the CLDR publication and lookup
tables. Both rules resolve a symbol/word token to an ISO 4217 code before
applying the shared amount validation (parse + strict over-precision
check).
"""

from __future__ import annotations

from typing import cast

from paxman.capabilities.Money.contract import MoneyContract
from paxman.capabilities.Money.notation import MoneyNotation
from paxman.capabilities.Money.parsing import (
    ParsedAmount,
    format_amount,
    parse_amount,
)
from paxman.capabilities.Money.rules.data.cldr_currencies import (
    NAME_TO_CODES,
    SYMBOL_TO_CODES,
)
from paxman.capabilities.Money.rules.data.iso4217_list_one import MINOR_UNITS
from paxman.core.contract import Contract
from paxman.core.domain import Provenance, Rule, RuleStrategy

# Case-insensitive fallback for word lookup: Money's WORD_TOKENS / NAME_TO_CODES
# keys are Title-Case ("Dollar"), but WordRecognition is case-insensitive
# (re.IGNORECASE) and preserves as-written ("euro"). Currency folds to lower
# and stores lower keys (D4); Money keeps Title-Case storage but must resolve
# any case variant. This lower map mirrors Currency's lower-key discipline
# without touching generated data.
_NAME_TO_CODES_LOWER: dict[str, tuple[str, ...]] = {
    k.lower(): v for k, v in NAME_TO_CODES.items()
}

PUBLICATION = Provenance(
    authority="Unicode CLDR",
    specification_name="Unicode CLDR",
    kind="specification",
    reference_url="https://cldr.unicode.org/",
    version="47",
    lifecycle="active",
    publication_year=2025,
)


def _resolve_symbol_code(
    notation: MoneyNotation,
    contract: MoneyContract,
) -> str | None:
    """Resolve a symbol/qualified_symbol notation to an ISO 4217 code.

    The matches() shape check has already gated acceptance, so definitiveness
    is decided purely by the mapping: a token with exactly one candidate
    resolves to it; a multi-candidate token (e.g. "$", the yen sign, or the
    letter-like "kr"/"L"/"Rs") resolves via the opt-in
    ``contract.dollar_sign_currency`` (default None). A multi-candidate
    symbol with ``dollar_sign_currency=None`` resolves to None, which makes
    matches() return False (INVALID, never silently dropped).

    Args:
        notation: Money notation to resolve.
        contract: Money contract (dollar_sign_currency).

    Returns:
        The resolved ISO 4217 code, or None when no code can be resolved.
    """
    codes = SYMBOL_TO_CODES.get(notation.currency_part)
    if codes is None:
        return None
    if len(codes) == 1:
        return codes[0]
    return contract.dollar_sign_currency


def _resolve_name_code(
    notation: MoneyNotation,
    contract: MoneyContract,
) -> str | None:
    """Resolve a word notation to an ISO 4217 code (case-insensitive).

    WordRecognition is case-insensitive (re.IGNORECASE) and preserves
    as-written (e.g. "euro"), while NAME_TO_CODES keys are Title-Case
    ("Euro"). The lookup is therefore case-insensitive via the lower-case
    fallback map (mirrors Currency's D4 lower folding without touching
    generated data). Single-candidate remains definitive; multi-candidate
    resolves via dollar_sign_currency.

    Args:
        notation: Money notation to resolve.
        contract: Money contract (dollar_sign_currency).

    Returns:
        The resolved ISO 4217 code, or None when no code can be resolved.
    """
    codes = NAME_TO_CODES.get(notation.currency_part)
    if codes is None:
        codes = _NAME_TO_CODES_LOWER.get(notation.currency_part.lower())
    if codes is None:
        return None
    if len(codes) == 1:
        return codes[0]
    return contract.dollar_sign_currency


def _amount_matches(
    parsed: ParsedAmount,
    code: str,
    contract: MoneyContract,
) -> bool:
    """Shared amount validation: parse result + strict over-precision check.

    The code comes from the CLDR tables or ``contract.dollar_sign_currency``;
    codes absent from MINOR_UNITS (e.g. a bad dollar_sign_currency value) are
    rejected defensively so neither this check nor normalize() can KeyError
    (rules never raise).

    Args:
        parsed: Parsed amount to check.
        code: Resolved ISO 4217 code.
        contract: Money contract (precision mode).

    Returns:
        True if the code is known and strict precision is not exceeded.
    """
    if code not in MINOR_UNITS:
        return False
    return not (
        contract.precision == "strict" and parsed.decimal_digits() > MINOR_UNITS[code]
    )


class SectionSymbols(Rule[MoneyNotation]):
    """CLDR Section: currency symbols.

    Validates "symbol"/"qualified_symbol" shapes. The token resolves to an
    ISO 4217 code (qualified or definitive via the table, multi-candidate
    via dollar_sign_currency), then the amount must parse and (in strict
    precision mode) not exceed that code's minor units. Accounting-form
    amounts (parenthesized) are rejected: the authority assigns no meaning
    to a parenthesized amount.
    """

    name = "Section-symbols"
    strategy = RuleStrategy.LOOKUP_TABLE
    provenance = PUBLICATION
    citation = "CLDR v47 currency symbols"
    target_semantics = frozenset({"symbol_recognition"})
    requires_features = frozenset()

    def matches(self, notation: MoneyNotation, contract: Contract) -> bool:
        """Check if the notation is a valid currency symbol with a valid amount.

        Args:
            notation: Money notation to validate.
            contract: Contract configuration.

        Returns:
            True if shape is "symbol"/"qualified_symbol", the amount is
            not accounting-form, a code can be resolved, and the amount
            passes the shared validation.
        """
        if notation.currency_shape not in ("symbol", "qualified_symbol"):
            return False
        if notation.amount_shape == "accounting":
            return False
        typed_contract = cast(MoneyContract, contract)
        code = _resolve_symbol_code(notation, typed_contract)
        if code is None:
            return False
        parsed = parse_amount(notation.amount_part)
        if parsed is None:
            return False
        return _amount_matches(parsed, code, typed_contract)

    def normalize(self, notation: MoneyNotation, contract: Contract) -> str:
        """Normalize to the canonical CODE + amount form.

        Args:
            notation: Validated notation.
            contract: Contract configuration.

        Returns:
            "{code} {amount}" where the amount is padded, rounded, or
            truncated to the resolved code's minor units.
        """
        typed_contract = cast(MoneyContract, contract)
        code = _resolve_symbol_code(notation, typed_contract)
        parsed = parse_amount(notation.amount_part)
        if code is None or code not in MINOR_UNITS or parsed is None:
            return notation.amount_part  # unreachable post-matches(); defensive
        minor_units = MINOR_UNITS[code]
        amount = format_amount(parsed, minor_units, typed_contract.precision)
        return f"{code} {amount}"


class SectionNames(Rule[MoneyNotation]):
    """CLDR Section: currency display names.

    Validates "word" shapes. The display name resolves to an ISO 4217 code
    (definitive via the table, multi-candidate via dollar_sign_currency), then
    the amount must parse and (in strict precision mode) not exceed that
    code's minor units. Accounting-form amounts (parenthesized) are
    rejected: the authority assigns no meaning to a parenthesized amount.
    """

    name = "Section-names"
    strategy = RuleStrategy.LOOKUP_TABLE
    provenance = PUBLICATION
    citation = "CLDR v47 currency display names"
    target_semantics = frozenset({"word_recognition"})
    requires_features = frozenset()

    def matches(self, notation: MoneyNotation, contract: Contract) -> bool:
        """Check if the notation is a valid display name with a valid amount.

        Args:
            notation: Money notation to validate.
            contract: Contract configuration.

        Returns:
            True if shape == "word", the amount is not accounting-form,
            a code can be resolved, and the amount passes the shared
            validation.
        """
        if notation.currency_shape != "word":
            return False
        if notation.amount_shape == "accounting":
            return False
        typed_contract = cast(MoneyContract, contract)
        code = _resolve_name_code(notation, typed_contract)
        if code is None:
            return False
        parsed = parse_amount(notation.amount_part)
        if parsed is None:
            return False
        return _amount_matches(parsed, code, typed_contract)

    def normalize(self, notation: MoneyNotation, contract: Contract) -> str:
        """Normalize to the canonical CODE + amount form.

        Args:
            notation: Validated notation.
            contract: Contract configuration.

        Returns:
            "{code} {amount}" where the amount is padded, rounded, or
            truncated to the resolved code's minor units.
        """
        typed_contract = cast(MoneyContract, contract)
        code = _resolve_name_code(notation, typed_contract)
        parsed = parse_amount(notation.amount_part)
        if code is None or code not in MINOR_UNITS or parsed is None:
            return notation.amount_part  # unreachable post-matches(); defensive
        minor_units = MINOR_UNITS[code]
        amount = format_amount(parsed, minor_units, typed_contract.precision)
        return f"{code} {amount}"
