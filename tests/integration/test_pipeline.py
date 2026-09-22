"""Integration tests for the engine orchestrator pipeline."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import pytest

from paxman.capabilities.Country.capability import CountryCapability
from paxman.capabilities.Date.capability import DateCapability
from paxman.capabilities.Email.capability import EmailCapability
from paxman.capabilities.Email.notation import EmailNotation
from paxman.capabilities.IP.capability import IPCapability
from paxman.capabilities.ISBN.capability import ISBNCapability
from paxman.capabilities.Phone.capability import PhoneCapability
from paxman.capabilities.SIUnit.capability import SIUnitCapability
from paxman.core.capability import Capability
from paxman.core.contract import Contract
from paxman.core.discovery import register_capability, reset_registry
from paxman.core.domain import (
    Grammar,
    Provenance,
    RecognitionMatch,
    Resolution,
    Rule,
    RuleStrategy,
)
from paxman.core.errors import (
    ContractError,
    MultipleMentionsError,
    RecognitionError,
    ValidationError,
)
from paxman.engine.orchestrator import run_capability


@pytest.fixture(autouse=True)
def _clean_registry():
    """Reset registry before each test."""
    reset_registry()
    yield
    reset_registry()


class TestRunCapability:
    @pytest.mark.integration
    def test_standard_email_success(self):
        cap = EmailCapability()
        register_capability(cap)

        contract = EmailCapability.create_contract()
        result = run_capability("Contact user@example.com", contract)

        assert result.status == Resolution.SUCCESS
        assert result.canonicalized_value == "user@example.com"
        assert len(result.candidates) >= 1

    @pytest.mark.integration
    def test_obfuscated_email_success(self):
        cap = EmailCapability()
        register_capability(cap)

        contract = EmailCapability.create_contract(include_obfuscated=True)
        result = run_capability("Email user at example dot com", contract)

        assert result.status == Resolution.SUCCESS
        assert result.canonicalized_value == "user@example.com"

    @pytest.mark.integration
    def test_localhost_email_success(self):
        cap = EmailCapability()
        register_capability(cap)

        contract = EmailCapability.create_contract()
        result = run_capability("Send to admin@localhost", contract)

        assert result.status == Resolution.SUCCESS
        assert result.canonicalized_value == "admin@localhost"

    @pytest.mark.integration
    def test_missing_input(self):
        cap = EmailCapability()
        register_capability(cap)

        contract = EmailCapability.create_contract()
        result = run_capability("no email here", contract)

        assert result.status == Resolution.MISSING
        assert result.canonicalized_value is None
        assert len(result.candidates) == 0

    @pytest.mark.integration
    def test_version_stamp_present(self):
        cap = EmailCapability()
        register_capability(cap)

        contract = EmailCapability.create_contract()
        result = run_capability("user@example.com", contract)

        assert result.version_stamp is not None
        assert isinstance(result.version_stamp.paxman_version, str)
        assert len(result.candidates) == 1
        assert {c.value for c in result.candidates} == {"user@example.com"}
        assert {p.authority for c in result.candidates for p in c.provenance} == {
            "IETF"
        }

    @pytest.mark.integration
    def test_canonical_determinism(self):
        cap = EmailCapability()
        register_capability(cap)

        contract = EmailCapability.create_contract()
        r1 = run_capability("user@example.com", contract)
        r2 = run_capability("user@example.com", contract)

        assert r1 == r2
        assert r1.status == r2.status
        assert r1.canonicalized_value == r2.canonicalized_value
        assert [c.value for c in r1.candidates] == [c.value for c in r2.candidates]
        assert len(r1.candidates) == 1
        assert {c.value for c in r1.candidates} == {"user@example.com"}
        assert {p.authority for c in r1.candidates for p in c.provenance} == {"IETF"}
        assert isinstance(r1.version_stamp.paxman_version, str)


# ---------------------------------------------------------------------------
# Error-wrapping stubs
# ---------------------------------------------------------------------------


class CrashGrammar(Grammar[EmailNotation]):
    """Grammar whose recognize() always raises."""

    name = "crash_grammar"
    semantics = "crash_grammar"

    def recognize(self, text: str) -> list[RecognitionMatch[EmailNotation]]:
        raise RuntimeError("grammar crashed")


class SimpleGrammar(Grammar[EmailNotation]):
    """Grammar that returns a fixed notation."""

    name = "simple_grammar"
    semantics = "simple_grammar"

    def recognize(self, text: str) -> list[RecognitionMatch[EmailNotation]]:
        return [
            RecognitionMatch(
                notation=EmailNotation(local_part="user", domain_part="example.com"),
                start=0,
                end=len(text),
                raw_text=text,
            )
        ]


class StubRule(Rule[EmailNotation]):
    """Rule that always matches."""

    name = "stub_rule"
    strategy = RuleStrategy.REGEX
    provenance = Provenance(
        authority="test",
        specification_name="test",
        kind="test",
        reference_url="https://test",
        version=None,
        lifecycle="active",
        publication_year=2024,
    )
    citation = "test"
    target_semantics = frozenset({"crash_grammar"})
    requires_features = frozenset()

    def matches(self, notation: EmailNotation, contract: object) -> bool:
        return True

    def normalize(self, notation: EmailNotation, contract: object) -> str:
        return "stub"


class ExplodingRule(Rule[EmailNotation]):
    """Rule whose matches() always raises."""

    name = "exploding_rule"
    strategy = RuleStrategy.REGEX
    provenance = Provenance(
        authority="test",
        specification_name="test",
        kind="test",
        reference_url="https://test",
        version=None,
        lifecycle="active",
        publication_year=2024,
    )
    citation = "test"
    target_semantics = frozenset({"simple_grammar"})
    requires_features = frozenset()

    def matches(self, notation: EmailNotation, contract: object) -> bool:
        raise ValueError("rule crashed")

    def normalize(self, notation: EmailNotation, contract: object) -> str:
        return "stub"


class CrashCapability(Capability):
    """Capability with a crashing grammar."""

    name = "crash"
    version = "0.1.0"

    def get_grammars(self) -> list[Grammar[EmailNotation]]:
        return [CrashGrammar()]

    def get_rules(self) -> list[Rule[EmailNotation]]:
        return [StubRule()]


class ExplodingRuleCapability(Capability):
    """Capability with a working grammar but crashing rule."""

    name = "exploding_rule_cap"
    version = "0.1.0"

    def get_grammars(self) -> list[Grammar[EmailNotation]]:
        return [SimpleGrammar()]

    def get_rules(self) -> list[Rule[EmailNotation]]:
        return [ExplodingRule()]


class _ErrorContract:
    """Minimal contract stub for error-wrapping tests."""

    @property
    def capability_name(self) -> str:
        return "crash"

    @property
    def active_grammars(self) -> list[str]:
        return ["crash_grammar"]

    @property
    def extra_grammars(self) -> tuple[str, ...]:
        return ()

    @property
    def excluded_rules(self) -> list[str]:
        return []

    @property
    def pinned_rules(self) -> list[str] | None:
        return None

    @property
    def year(self) -> int | None:
        return None

    @property
    def output_format(self) -> str | None:
        return None


class _ExplodingContract(_ErrorContract):
    """Contract variant for ExplodingRuleCapability."""

    @property
    def capability_name(self) -> str:
        return "exploding_rule_cap"

    @property
    def active_grammars(self) -> list[str]:
        return ["simple_grammar"]


class TestErrorWrapping:
    """Verify orchestrator wraps grammar/rule exceptions correctly."""

    @pytest.mark.integration
    def test_recognition_error_wrapped(self) -> None:
        register_capability(CrashCapability())
        contract = _ErrorContract()
        with pytest.raises(RecognitionError):
            run_capability("test input", contract)

    @pytest.mark.integration
    def test_validation_error_wrapped(self) -> None:
        register_capability(ExplodingRuleCapability())
        contract = _ExplodingContract()
        with pytest.raises(ValidationError):
            run_capability("test input", contract)


class TestPinnedRules:
    """Verify pinned_rules filtering behavior."""

    @pytest.mark.integration
    def test_pinned_rules_excludes_unpinned(self) -> None:
        register_capability(EmailCapability())
        contract = EmailCapability.create_contract(
            pinned_rules=("Section 3.4.1-addr-spec",)
        )
        result = run_capability("Send to admin@localhost", contract)

        assert result.status == Resolution.INVALID
        assert len(result.candidates) == 0

    @pytest.mark.integration
    def test_pinned_rules_only_runs_pinned(self) -> None:
        register_capability(EmailCapability())
        contract = EmailCapability.create_contract(
            pinned_rules=("Section 6.3-localhost",)
        )
        result = run_capability("Send to admin@localhost", contract)

        assert result.status == Resolution.SUCCESS
        assert result.canonicalized_value == "admin@localhost"
        assert len(result.candidates) == 1
        assert result.candidates[0].validation_rule == "Section 6.3-localhost"

    @pytest.mark.integration
    def test_pinned_rules_overrides_excluded_rules(self) -> None:
        register_capability(EmailCapability())
        contract = EmailCapability.create_contract(
            excluded_rules=["Section 6.3-localhost"],
            pinned_rules=("Section 6.3-localhost",),
        )
        result = run_capability("Send to admin@localhost", contract)

        assert result.status == Resolution.SUCCESS
        assert result.canonicalized_value == "admin@localhost"

    @pytest.mark.integration
    def test_pinned_rules_with_year_filter(self) -> None:
        register_capability(EmailCapability())
        contract = EmailCapability.create_contract(
            pinned_rules=("Section 3.4.1-addr-spec", "Section 6.3-localhost"),
            year=2010,
        )
        result = run_capability("Send to admin@localhost", contract)

        assert result.status == Resolution.INVALID
        assert len(result.candidates) == 0

    @pytest.mark.integration
    def test_pinned_rules_none_uses_excluded_rules(self) -> None:
        register_capability(EmailCapability())
        contract = EmailCapability.create_contract(
            excluded_rules=["Section 6.3-localhost"]
        )
        result = run_capability("Send to admin@localhost", contract)

        assert result.status == Resolution.INVALID

    @pytest.mark.integration
    def test_pinned_rules_empty_tuple_excludes_all(self) -> None:
        register_capability(EmailCapability())
        contract = EmailCapability.create_contract(pinned_rules=())
        result = run_capability("user@example.com", contract)

        assert result.status == Resolution.INVALID
        assert len(result.candidates) == 0


class _PhantomGrammar(Grammar[EmailNotation]):
    """Grammar referenced by a rule that does not exist in the capability."""

    name = "phantom_grammar"
    semantics = "phantom_grammar"

    def recognize(self, text: str) -> list[RecognitionMatch[EmailNotation]]:
        return [
            RecognitionMatch(
                notation=EmailNotation(local_part="user", domain_part="example.com"),
                start=0,
                end=len(text),
                raw_text=text,
            )
        ]


class _PhantomRule(Rule[EmailNotation]):
    """Rule whose target_semantics names a non-existent grammar."""

    name = "phantom_rule"
    strategy = RuleStrategy.REGEX
    provenance = Provenance(
        authority="test",
        specification_name="test",
        kind="test",
        reference_url="https://test",
        version=None,
        lifecycle="active",
        publication_year=2024,
    )
    citation = "test"
    target_semantics = frozenset({"does_not_exist"})
    requires_features = frozenset()

    def matches(self, notation: EmailNotation, contract: object) -> bool:
        return True

    def normalize(self, notation: EmailNotation, contract: object) -> str:
        return "phantom"


class _PhantomCapability(Capability[EmailNotation]):
    """Capability whose rule declares a grammar the capability lacks."""

    name = "phantom"
    version = "0.1.0"

    def get_grammars(self) -> list[Grammar[EmailNotation]]:
        return [_PhantomGrammar()]

    def get_rules(self) -> list[Rule[EmailNotation]]:
        return [_PhantomRule()]


class _PhantomContract:
    """Minimal contract stub for the phantom capability."""

    @property
    def capability_name(self) -> str:
        return "phantom"

    @property
    def active_grammars(self) -> list[str]:
        return ["phantom_grammar"]

    @property
    def extra_grammars(self) -> tuple[str, ...]:
        return ()

    @property
    def excluded_rules(self) -> list[str]:
        return []

    @property
    def pinned_rules(self) -> list[str] | None:
        return None

    @property
    def year(self) -> int | None:
        return None

    @property
    def output_format(self) -> str | None:
        return None


class TestGrammarRuleAffinity:
    """F1: grammar→rule affinity declared via Rule.target_semantics."""

    @pytest.mark.integration
    @pytest.mark.parametrize("output_format", [None, "ISO", "US"])
    def test_date_ambiguity_holds_for_every_output_format(
        self, output_format: str | None
    ) -> None:
        """01/02/2026 is recognized by both US and EU grammars; both rules
        validate both notations, yielding two distinct canonical dates.

        Status reads the canonical, pre-format values: two distinct
        canonical dates make the result AMBIGUOUS for every requested
        format, and the surfaced candidates remain two distinct formatted
        values under each.
        """
        register_capability(DateCapability())
        contract = DateCapability.create_contract(output_format=output_format)
        result = run_capability("01/02/2026", contract)

        # Identity reads canonical values: two distinct canonical dates ->
        # AMBIGUOUS regardless of how each is rendered.
        assert result.status == Resolution.AMBIGUOUS
        assert len(result.candidates) == 4
        # Two genuinely distinct values -> AMBIGUOUS (not SUCCESS).
        assert len({c.value for c in result.candidates}) == 2

    @pytest.mark.integration
    def test_date_same_interpretation_is_success(self) -> None:
        """When both slash interpretations agree, F1 must not invent ambiguity."""
        register_capability(DateCapability())
        contract = DateCapability.create_contract()
        result = run_capability("12/12/2026", contract)

        assert result.status == Resolution.SUCCESS
        assert result.canonicalized_value == "2026-12-12"

    @pytest.mark.integration
    def test_date_ambiguity_formatted_values_remain_two_distinct(self) -> None:
        """The two canonical dates stay distinct after formatting.

        Status reads the canonical values, so the result is AMBIGUOUS in
        both cases; the default ISO and requested US formats each render
        the two distinct canonical dates as two distinct formatted values,
        so the surfaced candidate values stay two distinct across formats.
        """
        register_capability(DateCapability())
        base = run_capability("01/02/2026", DateCapability.create_contract())
        us = run_capability(
            "01/02/2026", DateCapability.create_contract(output_format="US")
        )

        assert base.status == us.status == Resolution.AMBIGUOUS
        # Each format renders the two distinct canonical dates as two distinct
        # formatted values; the number of distinct formatted candidate values
        # (and therefore the ambiguity) is invariant across formats.
        assert len({c.value for c in base.candidates}) == 2
        assert len({c.value for c in us.candidates}) == 2

    @pytest.mark.integration
    def test_affinity_validation_rejects_unknown_grammar(self) -> None:
        """A rule declaring a grammar the capability lacks must fail fast with
        ContractError, not silently drop the rule (which would yield INVALID)."""
        register_capability(_PhantomCapability())
        with pytest.raises(ContractError):
            run_capability("test input", _PhantomContract())


class TestCanonicalDeterminismAndCandidateOrder:
    """Canonical determinism and candidate order across capabilities.

    Each fixed input+contract is run twice; the second run must reproduce the
    first run's status, canonicalized value, and candidate tuple (order
    included). These regressions lock within-run determinism for formatted
    cases.
    """

    @pytest.mark.integration
    @pytest.mark.parametrize(
        ("capability_cls", "contract_factory", "input_text"),
        [
            pytest.param(
                DateCapability,
                lambda: DateCapability.create_contract(output_format="US"),
                "01/02/2026",
                id="date-ambiguous-us",
            ),
            pytest.param(
                PhoneCapability,
                lambda: PhoneCapability.create_contract(output_format="rfc3966"),
                "tel:+15551234567;ext=890",
                id="phone-rfc3966-extension",
            ),
            pytest.param(
                CountryCapability,
                lambda: CountryCapability.create_contract(output_format="alpha3"),
                "DE",
                id="country-alpha3",
            ),
            pytest.param(
                EmailCapability,
                lambda: EmailCapability.create_contract(),
                "user@example.com",
                id="email-default",
            ),
            pytest.param(
                IPCapability,
                lambda: IPCapability.create_contract(),
                "192.0.2.1",
                id="ip-default",
            ),
            pytest.param(
                ISBNCapability,
                lambda: ISBNCapability.create_contract(output_format="hyphenated"),
                "978-0-11-000222-4",
                id="isbn-hyphenated",
            ),
            pytest.param(
                ISBNCapability,
                lambda: ISBNCapability.create_contract(),
                "0306406152",
                id="isbn10-default",
            ),
            pytest.param(
                SIUnitCapability,
                lambda: SIUnitCapability.create_contract(),
                "megahertz",
                id="si_unit-prefixed-name",
            ),
        ],
    )
    def test_repeated_run_is_deterministic(
        self,
        capability_cls: type[Capability[Any]],
        contract_factory: Callable[[], Contract],
        input_text: str,
    ) -> None:
        """Running the same case twice yields identical results."""
        register_capability(capability_cls())
        contract = contract_factory()

        first = run_capability(input_text, contract)
        second = run_capability(input_text, contract)

        assert second == first
        assert second.status == first.status
        assert second.canonicalized_value == first.canonicalized_value
        assert second.candidates == first.candidates
        assert len(second.candidates) >= 1
        assert isinstance(second.version_stamp.paxman_version, str)

    @pytest.mark.integration
    def test_phone_extension_pair_status_is_format_invariant(self) -> None:
        """Two tel URIs sharing one canonical E.164 coalesce under any format.

        Status reads canonical, pre-format values, so the offered rfc3966
        format cannot flip the outcome relative to the default contract:
        both resolve the extension pair to SUCCESS (one entity — the
        canonical does not carry ``;ext=``), each rendering its own
        presentation of the first mention. Before formatting moved to result
        assembly, rfc3966 raised MultipleMentionsError here while the
        default contract succeeded. Genuine multi-number input still fails
        fast — see tests/integration/test_phone_pipeline.py.
        """
        register_capability(PhoneCapability())
        text = "tel:+15551234567;ext=890 and tel:+15551234567;ext=891"

        rfc3966 = run_capability(
            text, PhoneCapability.create_contract(output_format="rfc3966")
        )
        default = run_capability(text, PhoneCapability.create_contract())

        assert rfc3966.status is Resolution.SUCCESS
        assert default.status is Resolution.SUCCESS
        assert rfc3966.canonicalized_value == "tel:+15551234567;ext=890"
        assert default.canonicalized_value == "+15551234567"
        assert rfc3966.version_stamp == default.version_stamp


class TestISBNPipeline:
    """Integration resolution map for the ISBN capability (memo §7.6)."""

    @pytest.mark.integration
    def test_isbn13_bare_success(self) -> None:
        register_capability(ISBNCapability())
        contract = ISBNCapability.create_contract()
        result = run_capability("9780306406157", contract)

        assert result.status == Resolution.SUCCESS
        assert result.canonicalized_value == "9780306406157"
        assert len(result.candidates) >= 1

    @pytest.mark.integration
    def test_isbn13_hyphenated_success(self) -> None:
        register_capability(ISBNCapability())
        contract = ISBNCapability.create_contract()
        result = run_capability("978-0-306-40615-7", contract)

        assert result.status == Resolution.SUCCESS
        assert result.canonicalized_value == "9780306406157"

    @pytest.mark.integration
    def test_isbn13_labeled_success(self) -> None:
        register_capability(ISBNCapability())
        contract = ISBNCapability.create_contract()
        result = run_capability("ISBN 9780306406157", contract)

        assert result.status == Resolution.SUCCESS
        assert result.canonicalized_value == "9780306406157"

    @pytest.mark.integration
    def test_isbn10_success(self) -> None:
        register_capability(ISBNCapability())
        contract = ISBNCapability.create_contract()
        result = run_capability("0306406152", contract)

        assert result.status == Resolution.SUCCESS
        assert result.canonicalized_value == "9780306406157"

    @pytest.mark.integration
    def test_isbn10_x_folds(self) -> None:
        register_capability(ISBNCapability())
        contract = ISBNCapability.create_contract()
        result = run_capability("080442957x", contract)

        assert result.status == Resolution.SUCCESS
        assert result.canonicalized_value == "9780804429573"

    @pytest.mark.integration
    def test_cross_shape_collapse_success(self) -> None:
        """The ISBN-10 sub-run is contained in the ISBN-13 match; both
        normalize to the same value, so the result is SUCCESS, never
        AMBIGUOUS (memo §7.2)."""
        register_capability(ISBNCapability())
        contract = ISBNCapability.create_contract()
        result = run_capability("ISBN 978-0-306-40615-7 and 0-306-40615-2", contract)

        assert result.status == Resolution.SUCCESS
        assert result.canonicalized_value == "9780306406157"

    @pytest.mark.integration
    def test_bad_check_digit_invalid(self) -> None:
        register_capability(ISBNCapability())
        contract = ISBNCapability.create_contract()
        result = run_capability("9780306406158", contract)

        assert result.status == Resolution.INVALID
        assert len(result.candidates) == 0

    @pytest.mark.integration
    def test_unallocated_range_default_success(self) -> None:
        """Valid check digit; range rule off by default. Range is a
        provenance amplifier, not a validity gate."""
        register_capability(ISBNCapability())
        contract = ISBNCapability.create_contract()
        result = run_capability("9789990000009", contract)

        assert result.status == Resolution.SUCCESS
        assert result.canonicalized_value == "9789990000009"

    @pytest.mark.integration
    def test_unallocated_range_with_validation_success(self) -> None:
        """Range rule adds no provenance (unallocated) but the check-digit
        rule still validates."""
        register_capability(ISBNCapability())
        contract = ISBNCapability.create_contract(include_range_validation=True)
        result = run_capability("9789990000009", contract)

        assert result.status == Resolution.SUCCESS
        assert result.canonicalized_value == "9789990000009"

    @pytest.mark.integration
    def test_two_books_ambiguous(self) -> None:
        """Two ISBNs in one input fail fast (single-value invariant).

        Two books are un-segmented multi-entity input; the engine raises
        MultipleMentionsError rather than returning AMBIGUOUS.
        """
        register_capability(ISBNCapability())
        contract = ISBNCapability.create_contract()
        with pytest.raises(MultipleMentionsError):
            run_capability("9780306406157 and 9780201310054", contract)

    @pytest.mark.integration
    def test_missing_yields_missing(self) -> None:
        register_capability(ISBNCapability())
        contract = ISBNCapability.create_contract()
        result = run_capability("no isbn here", contract)

        assert result.status == Resolution.MISSING
        assert len(result.candidates) == 0

    @pytest.mark.integration
    def test_hyphenated_output_format(self) -> None:
        """Formatting precedes dedup; the bare value stays the candidate
        identity."""
        register_capability(ISBNCapability())
        contract = ISBNCapability.create_contract(output_format="hyphenated")
        result = run_capability("978-0-11-000222-4", contract)

        assert result.status == Resolution.SUCCESS
        assert result.canonicalized_value == "978-0-11-000222-4"

    @pytest.mark.integration
    def test_isbn10_conversion_0849396409(self) -> None:
        register_capability(ISBNCapability())
        contract = ISBNCapability.create_contract()
        result = run_capability("0849396409", contract)

        assert result.status == Resolution.SUCCESS
        assert result.canonicalized_value == "9780849396403"
