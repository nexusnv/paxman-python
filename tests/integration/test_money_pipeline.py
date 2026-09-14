"""Integration tests for the Money capability pipeline."""

import pytest

from paxman.capabilities.Money.capability import MoneyCapability
from paxman.core.discovery import register_capability, reset_registry
from paxman.core.domain import Resolution
from paxman.core.errors import MultipleMentionsError
from paxman.engine.orchestrator import run_capability


@pytest.fixture(autouse=True)
def _fresh_registry() -> None:
    """Reset the capability registry before and after each test."""
    reset_registry()
    yield
    reset_registry()


class TestMoneyPipeline:
    """Full-pipeline tests for the Money capability.

    Locked semantics:
    - the code grammar is case-sensitive ``[A-Z]{3}`` (research doc §7.2):
      lowercase ``usd 500`` is not recognized -> MISSING;
    - money only recognizes currency+amount together: a bare amount
      (``500``) or a bare currency (``USD``) alone is not recognized ->
      MISSING;
    - D6 single-currency precedence (research doc §9): a prefix symbol and
      a suffix code claiming the same amount collapse to one canonical
      value (never AMBIGUOUS). With the default ``dollar_sign_currency=None``
      the bare ``$`` yields no candidate, so ``$1,432.00 USD`` resolves via
      the suffix code (the ``$`` is non-matching context);
    - last-separator-wins amount parsing (user ruling): the final ``,`` or
      ``.`` is the decimal point, earlier separators are grouping;
    - AMBIGUOUS arises only from genuinely different canonical values:
      cross-grammar overlap (a symbol and a word both claiming the same
      amount) or multiple amounts with different currencies.
    """

    @pytest.mark.integration
    def test_success_code_prefix(self) -> None:
        """USD500 resolves to the padded canonical value."""
        register_capability(MoneyCapability())
        contract = MoneyCapability.create_contract()
        result = run_capability("USD500", contract)
        assert result.status == Resolution.SUCCESS
        assert result.canonicalized_value == "USD 500.00"

    @pytest.mark.integration
    def test_lowercase_code_missing(self) -> None:
        """The code grammar is case-sensitive; lowercase codes are MISSING."""
        register_capability(MoneyCapability())
        contract = MoneyCapability.create_contract()
        result = run_capability("usd 500", contract)
        assert result.status == Resolution.MISSING

    @pytest.mark.integration
    def test_success_qualified_symbol(self) -> None:
        """US$50.79 resolves via the qualified symbol to USD."""
        register_capability(MoneyCapability())
        contract = MoneyCapability.create_contract()
        result = run_capability("US$50.79", contract)
        assert result.status == Resolution.SUCCESS
        assert result.canonicalized_value == "USD 50.79"

    @pytest.mark.integration
    def test_success_code_suffix(self) -> None:
        """100MYR resolves via the suffix code."""
        register_capability(MoneyCapability())
        contract = MoneyCapability.create_contract()
        result = run_capability("100MYR", contract)
        assert result.status == Resolution.SUCCESS
        assert result.canonicalized_value == "MYR 100.00"

    @pytest.mark.integration
    def test_success_word(self) -> None:
        """18 Dollar resolves via the CLDR word table to USD."""
        register_capability(MoneyCapability())
        contract = MoneyCapability.create_contract()
        result = run_capability("18 Dollar", contract)
        assert result.status == Resolution.SUCCESS
        assert result.canonicalized_value == "USD 18.00"

    @pytest.mark.integration
    def test_bare_symbol_default_contract_invalid(self) -> None:
        """$500 with the default contract (dollar_sign_currency=None) is INVALID."""
        register_capability(MoneyCapability())
        contract = MoneyCapability.create_contract()
        result = run_capability("$500", contract)
        assert result.status == Resolution.INVALID
        assert result.candidates == ()

    @pytest.mark.integration
    def test_bare_symbol_opt_in_dollar_sign_currency(self) -> None:
        """$500 with dollar_sign_currency=USD (a $ candidate) resolves to USD 500.00."""
        register_capability(MoneyCapability())
        contract = MoneyCapability.create_contract(dollar_sign_currency="USD")
        result = run_capability("$500", contract)
        assert result.status == Resolution.SUCCESS
        assert result.canonicalized_value == "USD 500.00"

    @pytest.mark.integration
    def test_bare_symbol_non_candidate_dollar_sign_currency_invalid(self) -> None:
        """$500 with dollar_sign_currency=MYR (not a $ candidate) is INVALID (#15,
        parity with Currency's default_currency guard)."""
        register_capability(MoneyCapability())
        contract = MoneyCapability.create_contract(dollar_sign_currency="MYR")
        result = run_capability("$500", contract)
        assert result.status == Resolution.INVALID
        assert result.canonicalized_value is None

    @pytest.mark.integration
    def test_qualified_symbol_rm_with_myr_contract(self) -> None:
        """RM500 is definitive for MYR: resolves under an MYR contract (#15)."""
        register_capability(MoneyCapability())
        contract = MoneyCapability.create_contract(dollar_sign_currency="MYR")
        result = run_capability("RM500", contract)
        assert result.status == Resolution.SUCCESS
        assert result.canonicalized_value == "MYR 500.00"

    @pytest.mark.integration
    def test_qualified_code_form_reentry(self) -> None:
        """MYR 500.00 (qualified code form) re-enters as SUCCESS (#15)."""
        register_capability(MoneyCapability())
        contract = MoneyCapability.create_contract()
        result = run_capability("MYR 500.00", contract)
        assert result.status == Resolution.SUCCESS
        assert result.canonicalized_value == "MYR 500.00"

    @pytest.mark.integration
    def test_bare_symbol_explicit_none_invalid(self) -> None:
        """$500 with dollar_sign_currency=None is recognized but unvalidated."""
        register_capability(MoneyCapability())
        contract = MoneyCapability.create_contract(dollar_sign_currency=None)
        result = run_capability("$500", contract)
        assert result.status == Resolution.INVALID

    @pytest.mark.integration
    def test_suffix_code_wins_over_unresolvable_symbol(self) -> None:
        """D6: $1,432.00 USD collapses to one canonical value, never AMBIGUOUS.

        With the default dollar_sign_currency=None the bare $ yields no
        candidate (SectionSymbols.matches() -> False), so the suffix code is
        the sole candidate: SUCCESS "USD 1432.00" with exactly one candidate.
        (Oracle review finding: this single-candidate assertion only holds
        because the symbol candidate is absent — under the old
        default_currency="USD" two same-valued candidates survived.)
        """
        register_capability(MoneyCapability())
        contract = MoneyCapability.create_contract()
        result = run_capability("$1,432.00 USD", contract)
        assert result.status == Resolution.SUCCESS
        assert result.canonicalized_value == "USD 1432.00"
        assert len(result.candidates) == 1
        assert {c.recognition_rule for c in result.candidates} == {"code_recognition"}

    @pytest.mark.integration
    def test_comma_decimal_european(self) -> None:
        """1.000,50 EUR: last separator is the decimal point."""
        register_capability(MoneyCapability())
        contract = MoneyCapability.create_contract()
        result = run_capability("1.000,50 EUR", contract)
        assert result.status == Resolution.SUCCESS
        assert result.canonicalized_value == "EUR 1000.50"

    @pytest.mark.integration
    def test_mixed_separators_last_wins(self) -> None:
        """1,00.50 USD: last separator (.) is the decimal point."""
        register_capability(MoneyCapability())
        contract = MoneyCapability.create_contract()
        result = run_capability("1,00.50 USD", contract)
        assert result.status == Resolution.SUCCESS
        assert result.canonicalized_value == "USD 1000.50"

    @pytest.mark.integration
    def test_success_definitive_symbol(self) -> None:
        """€5 resolves via the definitive EUR symbol."""
        register_capability(MoneyCapability())
        contract = MoneyCapability.create_contract()
        result = run_capability("\u20ac5", contract)
        assert result.status == Resolution.SUCCESS
        assert result.canonicalized_value == "EUR 5.00"

    @pytest.mark.integration
    def test_missing(self) -> None:
        """Nothing recognized."""
        register_capability(MoneyCapability())
        contract = MoneyCapability.create_contract()
        result = run_capability("gibberish", contract)
        assert result.status == Resolution.MISSING

    @pytest.mark.integration
    def test_bare_amount_missing(self) -> None:
        """A bare amount without a currency is not a money token (MISSING)."""
        register_capability(MoneyCapability())
        contract = MoneyCapability.create_contract()
        result = run_capability("500", contract)
        assert result.status == Resolution.MISSING

    @pytest.mark.integration
    def test_bare_currency_missing(self) -> None:
        """A bare currency without an amount is not a money token (MISSING)."""
        register_capability(MoneyCapability())
        contract = MoneyCapability.create_contract()
        result = run_capability("USD", contract)
        assert result.status == Resolution.MISSING

    @pytest.mark.integration
    def test_sign_adjacent_forms_missing(self) -> None:
        """Sign-adjacent tokens are MISSING: the sign must not be dropped.

        A '-' (or Unicode minus, U+2212) adjacent to the code, amount, or
        symbol is outside the money grammar; recognizing it would silently
        canonicalize the positive amount and lose the sign.
        """
        register_capability(MoneyCapability())
        contract = MoneyCapability.create_contract()
        for text in ("-500 USD", "\u2212500 USD", "-USD 500", "500 USD-"):
            result = run_capability(text, contract)
            assert result.status == Resolution.MISSING, text

    @pytest.mark.integration
    def test_accounting_parens_rejected(self) -> None:
        """(500) USD is recognized but INVALID: the sign must not be dropped.

        Accounting parentheses are outside the amount semantics; the rules
        reject the accounting shape so a negative amount never canonicalizes
        as positive.
        """
        register_capability(MoneyCapability())
        contract = MoneyCapability.create_contract()
        result = run_capability("(500) USD", contract)
        assert result.status == Resolution.INVALID
        assert result.canonicalized_value is None

    @pytest.mark.integration
    def test_cross_grammar_ambiguous(self) -> None:
        """A symbol and a word claiming the same amount are AMBIGUOUS.

        The euro symbol and the word Dollar both claim the amount 18; the
        engine keeps cross-grammar overlaps, so two different canonical
        values emerge.
        """
        register_capability(MoneyCapability())
        contract = MoneyCapability.create_contract()
        result = run_capability("\u20ac 18 Dollar", contract)
        assert result.status == Resolution.AMBIGUOUS
        assert result.canonicalized_value is None
        assert {c.value for c in result.candidates} == {"EUR 18.00", "USD 18.00"}

    @pytest.mark.integration
    def test_multi_amount_ambiguous(self) -> None:
        """Two amounts in one input fail fast (single-value invariant).

        Two amounts are un-segmented multi-entity input, so the engine raises
        MultipleMentionsError instead of returning AMBIGUOUS.
        """
        register_capability(MoneyCapability())
        contract = MoneyCapability.create_contract()
        with pytest.raises(MultipleMentionsError):
            run_capability("USD 100 and EUR 200", contract)

    @pytest.mark.integration
    def test_version_stamp(self) -> None:
        """Version stamp is present and canonicalization is deterministic."""
        register_capability(MoneyCapability())
        contract = MoneyCapability.create_contract()
        result1 = run_capability("USD500", contract)
        result2 = run_capability("USD500", contract)
        assert result1 == result2
        assert result1.status == result2.status
        assert result1.canonicalized_value == result2.canonicalized_value
        assert [c.value for c in result1.candidates] == [
            c.value for c in result2.candidates
        ]
        assert len(result1.candidates) == 1
        assert {c.value for c in result1.candidates} == {"USD 500.00"}
        assert {p.authority for c in result1.candidates for p in c.provenance} == {
            "ISO"
        }
        assert isinstance(result1.version_stamp.paxman_version, str)
