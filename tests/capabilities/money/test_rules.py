"""Tests for Money capability validation rules."""

from __future__ import annotations

import pytest

from paxman.capabilities.Money.contract import MoneyContract
from paxman.capabilities.Money.notation import MoneyNotation
from paxman.capabilities.Money.rules.cldr_currencies_ed2025 import (
    SectionNames,
    SectionSymbols,
)
from paxman.capabilities.Money.rules.iso_4217_ed2015 import SectionCode
from paxman.core.domain import RuleStrategy

pytestmark = [pytest.mark.capability]


def _notation(
    currency_part: str,
    amount_part: str,
    currency_shape: str,
    amount_shape: str = "integer",
) -> MoneyNotation:
    """Build a MoneyNotation directly (no grammar) for rule-level testing."""
    return MoneyNotation(
        currency_part=currency_part,
        amount_part=amount_part,
        currency_shape=currency_shape,
        amount_shape=amount_shape,
    )


class TestSectionCode:
    """Tests for SectionCode rule."""

    def setup_method(self) -> None:
        self.rule = SectionCode()

    def test_matches_valid_code(self) -> None:
        """Happy path: known code + integer amount matches."""
        contract = MoneyContract()
        notation = _notation("USD", "500", "code")
        assert self.rule.matches(notation, contract) is True

    @pytest.mark.parametrize(
        ("currency_part", "amount_part", "amount_shape", "expected"),
        [
            ("USD", "500", "integer", "USD 500.00"),
            ("JPY", "500", "integer", "JPY 500"),
            ("BHD", "500", "integer", "BHD 500.000"),
            ("EUR", "500.50", "dot_decimal", "EUR 500.50"),
        ],
    )
    def test_normalize_pads_to_minor_units(
        self,
        currency_part: str,
        amount_part: str,
        amount_shape: str,
        expected: str,
    ) -> None:
        """Canonical output pads the amount to the code's minor units (D2)."""
        contract = MoneyContract()
        notation = _notation(currency_part, amount_part, "code", amount_shape)
        assert self.rule.matches(notation, contract) is True
        assert self.rule.normalize(notation, contract) == expected

    def test_rejects_unknown_code(self) -> None:
        """Unknown code XYZ is not in the ISO 4217 List One table."""
        contract = MoneyContract()
        notation = _notation("XYZ", "500", "code")
        assert self.rule.matches(notation, contract) is False

    def test_rejects_lowercase_code(self) -> None:
        """Lowercase 'usd' is not in the uppercase CURRENCY_CODES table."""
        contract = MoneyContract()
        notation = _notation("usd", "500", "code")
        assert self.rule.matches(notation, contract) is False

    def test_rejects_wrong_shape(self) -> None:
        """A symbol-shaped notation is not validated by the code rule."""
        contract = MoneyContract()
        notation = _notation("USD", "500", "symbol")
        assert self.rule.matches(notation, contract) is False

    def test_rejects_non_digit_amount(self) -> None:
        """An amount with no digits fails parse_amount (defensive path)."""
        contract = MoneyContract()
        notation = _notation("USD", "abc", "code")
        assert self.rule.matches(notation, contract) is False

    def test_strict_rejects_over_precision(self) -> None:
        """USD 500.123 exceeds the 2 minor units: INVALID in strict mode."""
        contract = MoneyContract()
        notation = _notation("USD", "500.123", "code", "dot_decimal")
        assert self.rule.matches(notation, contract) is False

    def test_strict_rejects_jpy_fraction(self) -> None:
        """JPY has 0 minor units; 500.5 is over-precision in strict mode."""
        contract = MoneyContract()
        notation = _notation("JPY", "500.5", "code", "dot_decimal")
        assert self.rule.matches(notation, contract) is False

    @pytest.mark.parametrize(
        ("amount_part", "expected"),
        [
            ("500.5", "JPY 500"),
            ("2.5", "JPY 2"),
            ("3.5", "JPY 4"),
        ],
    )
    def test_round_precision_half_to_even(
        self, amount_part: str, expected: str
    ) -> None:
        """precision=round rounds half-to-even: 2.5 to 2, 3.5 to 4 (D2)."""
        contract = MoneyContract(precision="round")
        notation = _notation("JPY", amount_part, "code", "dot_decimal")
        assert self.rule.matches(notation, contract) is True
        assert self.rule.normalize(notation, contract) == expected

    def test_truncate_precision_drops_excess_digits(self) -> None:
        """precision=truncate drops digits past the minor unit (D2)."""
        contract = MoneyContract(precision="truncate")
        notation = _notation("USD", "500.999", "code", "dot_decimal")
        assert self.rule.matches(notation, contract) is True
        assert self.rule.normalize(notation, contract) == "USD 500.99"

    def test_provenance_attributes(self) -> None:
        """Verify authority, spec name, kind, year, lifecycle, version."""
        assert self.rule.provenance.authority == "ISO"
        assert self.rule.provenance.specification_name == "ISO 4217"
        assert self.rule.provenance.kind == "specification"
        assert self.rule.provenance.publication_year == 2015
        assert self.rule.provenance.lifecycle == "active"
        assert self.rule.provenance.version is None

    def test_rule_name(self) -> None:
        """Verify name follows the Section-{description} convention (Country style)."""
        assert self.rule.name == "Section-codes"

    def test_strategy(self) -> None:
        """Verify the rule strategy enum."""
        assert self.rule.strategy == RuleStrategy.LOOKUP_TABLE

    def test_target_semantics(self) -> None:
        """The code rule targets only the code grammar."""
        assert self.rule.target_semantics == frozenset({"code_recognition"})

    def test_requires_features_empty(self) -> None:
        """The ISO rule never gates on contract features (always runs)."""
        assert self.rule.requires_features == frozenset()

    def test_rejects_accounting_amount(self) -> None:
        """Accounting-form amounts are rejected: the sign would be dropped.

        The grammar recognizes "(500)" (accounting shape) and parse_amount
        keeps the digit run, so the rule must reject the shape — otherwise
        "(500) USD" would canonicalize a negative amount as positive.
        """
        contract = MoneyContract()
        notation = _notation("USD", "(500)", "code", "accounting")
        assert self.rule.matches(notation, contract) is False


class TestSectionSymbols:
    """Tests for SectionSymbols rule."""

    def setup_method(self) -> None:
        self.rule = SectionSymbols()

    def test_qualified_symbol_definitive(self) -> None:
        """US$ is a qualified symbol mapped definitively to USD."""
        contract = MoneyContract()
        notation = _notation("US$", "50.79", "qualified_symbol", "dot_decimal")
        assert self.rule.matches(notation, contract) is True
        assert self.rule.normalize(notation, contract) == "USD 50.79"

    def test_qualified_symbol_never_remapped(self) -> None:
        """A definitive qualified symbol ignores dollar_sign_currency (D3)."""
        contract = MoneyContract(dollar_sign_currency="CAD")
        notation = _notation("US$", "50.79", "qualified_symbol", "dot_decimal")
        assert self.rule.matches(notation, contract) is True
        assert self.rule.normalize(notation, contract) == "USD 50.79"

    def test_bare_symbol_resolves_via_dollar_sign_currency(self) -> None:
        """Bare $ with dollar_sign_currency=USD resolves to USD (D3)."""
        contract = MoneyContract(dollar_sign_currency="USD")
        notation = _notation("$", "500", "symbol")
        assert self.rule.matches(notation, contract) is True
        assert self.rule.normalize(notation, contract) == "USD 500.00"

    def test_bare_symbol_dollar_sign_currency_cad(self) -> None:
        """Bare $ with dollar_sign_currency=CAD resolves to CAD (D3)."""
        contract = MoneyContract(dollar_sign_currency="CAD")
        notation = _notation("$", "500", "symbol")
        assert self.rule.matches(notation, contract) is True
        assert self.rule.normalize(notation, contract) == "CAD 500.00"

    def test_bare_symbol_no_dollar_sign_currency_invalid(self) -> None:
        """Bare $ with dollar_sign_currency=None is INVALID, never dropped (D3)."""
        contract = MoneyContract(dollar_sign_currency=None)
        notation = _notation("$", "500", "symbol")
        assert self.rule.matches(notation, contract) is False

    def test_definitive_symbol_without_dollar_sign_currency(self) -> None:
        """Euro sign is definitive (EUR) and needs no dollar_sign_currency (D3)."""
        contract = MoneyContract(dollar_sign_currency=None)
        notation = _notation("\u20ac", "5", "symbol")
        assert self.rule.matches(notation, contract) is True
        assert self.rule.normalize(notation, contract) == "EUR 5.00"

    def test_definitive_symbol_default_contract(self) -> None:
        """Euro sign with the default contract (dollar_sign_currency=None) still
        resolves to EUR (D3).
        """
        contract = MoneyContract()
        notation = _notation("\u20ac", "5", "symbol")
        assert self.rule.matches(notation, contract) is True
        assert self.rule.normalize(notation, contract) == "EUR 5.00"

    def test_multi_candidate_symbol_dollar_sign_currency(self) -> None:
        """Yen sign (multi-candidate) resolves via dollar_sign_currency (D3)."""
        contract = MoneyContract(dollar_sign_currency="JPY")
        notation = _notation("\u00a5", "500", "symbol")
        assert self.rule.matches(notation, contract) is True
        assert self.rule.normalize(notation, contract) == "JPY 500"

    def test_strict_over_precision_through_symbol(self) -> None:
        """Euro 5.555 exceeds EUR's 2 minor units: INVALID in strict mode."""
        contract = MoneyContract()
        notation = _notation("\u20ac", "5.555", "symbol", "dot_decimal")
        assert self.rule.matches(notation, contract) is False

    def test_rejects_wrong_shape(self) -> None:
        """A code-shaped notation is not validated by the symbol rule."""
        contract = MoneyContract()
        notation = _notation("$", "500", "code")
        assert self.rule.matches(notation, contract) is False

    def test_rejects_unknown_symbol(self) -> None:
        """An unknown symbol token is not in SYMBOL_TO_CODES."""
        contract = MoneyContract()
        notation = _notation("\u20ac\u00a3", "500", "symbol")
        assert self.rule.matches(notation, contract) is False

    def test_provenance_attributes(self) -> None:
        """Verify authority, spec name, kind, year, lifecycle, version."""
        assert self.rule.provenance.authority == "Unicode CLDR"
        assert self.rule.provenance.specification_name == "Unicode CLDR"
        assert self.rule.provenance.kind == "specification"
        assert self.rule.provenance.publication_year == 2025
        assert self.rule.provenance.lifecycle == "active"
        assert self.rule.provenance.version == "47"

    def test_rule_name(self) -> None:
        """Verify name follows the Section-{description} convention (Country style)."""
        assert self.rule.name == "Section-symbols"

    def test_strategy(self) -> None:
        """Verify the rule strategy enum."""
        assert self.rule.strategy == RuleStrategy.LOOKUP_TABLE

    def test_target_semantics(self) -> None:
        """The symbol rule targets only the symbol grammar."""
        assert self.rule.target_semantics == frozenset({"symbol_recognition"})

    def test_requires_features_empty(self) -> None:
        """Never gate on dollar_sign_currency: bare $ yields INVALID, not MISSING."""
        assert self.rule.requires_features == frozenset()

    def test_rejects_accounting_amount(self) -> None:
        """Accounting-form amounts are rejected: the sign would be dropped."""
        contract = MoneyContract()
        notation = _notation("\u20ac", "(500)", "symbol", "accounting")
        assert self.rule.matches(notation, contract) is False

    @pytest.mark.parametrize(
        "symbol",
        ["L", "Rs", "kr"],
    )
    def test_qualified_multi_candidate_symbol_default_contract_invalid(
        self, symbol: str
    ) -> None:
        """A letter-like multi-candidate symbol (L/Rs/kr) in qualified shape
        must not silently resolve to the alphabetically-first code under the
        default contract: it is ambiguous, so matches() is False (D3).
        """
        contract = MoneyContract()
        notation = _notation(symbol, "500", "qualified_symbol")
        assert self.rule.matches(notation, contract) is False

    @pytest.mark.parametrize(
        ("symbol", "code", "expected"),
        [
            ("kr", "SEK", "SEK 500.00"),
            ("L", "RON", "RON 500.00"),
        ],
    )
    def test_qualified_multi_candidate_symbol_dollar_sign_currency(
        self, symbol: str, code: str, expected: str
    ) -> None:
        """A letter-like multi-candidate symbol resolves only via the opt-in
        dollar_sign_currency (D3).
        """
        contract = MoneyContract(dollar_sign_currency=code)
        notation = _notation(symbol, "500", "qualified_symbol")
        assert self.rule.matches(notation, contract) is True
        assert self.rule.normalize(notation, contract) == expected

    def test_multi_candidate_symbol_bad_dollar_sign_currency_guard(self) -> None:
        """A bare multi-candidate symbol with a shape-valid but unknown
        dollar_sign_currency (ZZZ) is INVALID and never raises (the
        MINOR_UNITS guard in _amount_matches).
        """
        contract = MoneyContract(dollar_sign_currency="ZZZ")
        notation = _notation("$", "500", "symbol")
        assert self.rule.matches(notation, contract) is False

    def test_bare_symbol_dollar_sign_currency_non_candidate_override(self) -> None:
        """dollar_sign_currency overrides unconditionally: $ with EUR (not in
        the $ candidate tuple) resolves to EUR (D3).
        """
        contract = MoneyContract(dollar_sign_currency="EUR")
        notation = _notation("$", "500", "symbol")
        assert self.rule.matches(notation, contract) is True
        assert self.rule.normalize(notation, contract) == "EUR 500.00"


class TestSectionNames:
    """Tests for SectionNames rule."""

    def setup_method(self) -> None:
        self.rule = SectionNames()

    def test_definitive_word_dollar(self) -> None:
        """Dollar is a definitive display name for USD."""
        contract = MoneyContract()
        notation = _notation("Dollar", "18", "word")
        assert self.rule.matches(notation, contract) is True
        assert self.rule.normalize(notation, contract) == "USD 18.00"

    def test_definitive_word_euro(self) -> None:
        """Euro resolves to EUR regardless of dollar_sign_currency (D3)."""
        contract = MoneyContract()
        notation = _notation("Euro", "5", "word")
        assert self.rule.matches(notation, contract) is True
        assert self.rule.normalize(notation, contract) == "EUR 5.00"

    def test_rejects_unknown_word(self) -> None:
        """Zorkmids is not a CLDR currency display name."""
        contract = MoneyContract()
        notation = _notation("Zorkmids", "18", "word")
        assert self.rule.matches(notation, contract) is False

    def test_rejects_wrong_shape(self) -> None:
        """A symbol-shaped notation is not validated by the word rule."""
        contract = MoneyContract()
        notation = _notation("Euro", "5", "symbol")
        assert self.rule.matches(notation, contract) is False

    def test_provenance_attributes(self) -> None:
        """Verify authority, spec name, kind, year, lifecycle, version."""
        assert self.rule.provenance.authority == "Unicode CLDR"
        assert self.rule.provenance.specification_name == "Unicode CLDR"
        assert self.rule.provenance.kind == "specification"
        assert self.rule.provenance.publication_year == 2025
        assert self.rule.provenance.lifecycle == "active"
        assert self.rule.provenance.version == "47"

    def test_rule_name(self) -> None:
        """Verify name follows the Section-{description} convention (Country style)."""
        assert self.rule.name == "Section-names"

    def test_strategy(self) -> None:
        """Verify the rule strategy enum."""
        assert self.rule.strategy == RuleStrategy.LOOKUP_TABLE

    def test_target_semantics(self) -> None:
        """The word rule targets only the word grammar."""
        assert self.rule.target_semantics == frozenset({"word_recognition"})

    def test_requires_features_empty(self) -> None:
        """The CLDR name rule never gates on contract features."""
        assert self.rule.requires_features == frozenset()

    def test_rejects_accounting_amount(self) -> None:
        """Accounting-form amounts are rejected: the sign would be dropped."""
        contract = MoneyContract()
        notation = _notation("Euro", "(500)", "word", "accounting")
        assert self.rule.matches(notation, contract) is False

    @pytest.mark.parametrize(
        ("word", "raw_amount", "expected"),
        [
            ("euro", "5", "EUR 5.00"),
            ("EURO", "5", "EUR 5.00"),
            ("EuRo", "5", "EUR 5.00"),
            ("dollar", "18", "USD 18.00"),
            ("DOLLAR", "18", "USD 18.00"),
            ("DoLlAr", "18", "USD 18.00"),
            ("ringgit", "500", "MYR 500.00"),
            ("RINGGIT", "500", "MYR 500.00"),
        ],
    )
    def test_case_insensitive_word_variants(
        self, word: str, raw_amount: str, expected: str
    ) -> None:
        """Word lookup is case-insensitive: any casing of a Title-Case key validates.

        Grammar is case-insensitive (re.IGNORECASE) and preserves as-written;
        the rule normalizes via the lower fallback map (D4 divergence from
        Currency's lower folding). Regression for audit #137 B1.
        """
        contract = MoneyContract()
        notation = _notation(word, raw_amount, "word", "integer")
        assert self.rule.matches(notation, contract) is True
        assert self.rule.normalize(notation, contract) == expected
