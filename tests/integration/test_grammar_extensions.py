"""Integration tests for the community grammar extension seam."""

from __future__ import annotations

import re
from collections.abc import Iterator
from datetime import datetime

import pytest

from paxman.capabilities.Date.capability import DateCapability
from paxman.capabilities.Date.contract import DateContract
from paxman.capabilities.Date.notation import DateNotation
from paxman.capabilities.Date.rules.iso_8601_ed2019 import PUBLICATION
from paxman.core.contract import Contract
from paxman.core.discovery import register_capability, reset_registry
from paxman.core.domain import (
    Grammar,
    RecognitionMatch,
    Resolution,
    Rule,
    RuleStrategy,
)
from paxman.core.errors import CapabilityError, ContractError
from paxman.core.extensions import (
    register_grammar,
    register_rule,
    reset_extensions,
)
from paxman.engine.orchestrator import run_capability

# --- Community test doubles ---


class DotDateGrammar(Grammar[DateNotation]):
    """Community test double: recognizes YYYY.MM.DD (dot separator)."""

    name = "dot_date_recognition"
    semantics = "dot_date_recognition"
    _PATTERN = re.compile(r"\b(\d{4})\.(\d{2})\.(\d{2})\b")

    def recognize(self, text: str) -> list[RecognitionMatch[DateNotation]]:
        """Extract dot-separated date patterns."""
        return [
            RecognitionMatch(
                notation=DateNotation(N1=m.group(1), N2=m.group(2), N3=m.group(3)),
                start=m.start(),
                end=m.end(),
                raw_text=m.group(0),
            )
            for m in self._PATTERN.finditer(text)
        ]


class SecondDateGrammar(Grammar[DateNotation]):
    """Second community test double — same shape, different normalization."""

    name = "second_recognition"
    semantics = "second_recognition"
    _PATTERN = re.compile(r"\b(\d{4})\.(\d{2})\.(\d{2})\b")

    def recognize(self, text: str) -> list[RecognitionMatch[DateNotation]]:
        """Extract the same dot-separated date patterns."""
        return [
            RecognitionMatch(
                notation=DateNotation(N1=m.group(1), N2=m.group(2), N3=m.group(3)),
                start=m.start(),
                end=m.end(),
                raw_text=m.group(0),
            )
            for m in self._PATTERN.finditer(text)
        ]


class ClashingDateGrammar(Grammar[DateNotation]):
    """Community grammar whose name collides with a shipped Date grammar."""

    name = "date_recognition"
    semantics = "date_calendar_date"

    def recognize(self, text: str) -> list[RecognitionMatch[DateNotation]]:
        return []


class DotDateRule(Rule[DateNotation]):
    """Community test double: validates the dot-date grammar."""

    name = "dot_date_rule"
    strategy = RuleStrategy.PARSER
    provenance = PUBLICATION
    citation = "community test double"
    target_semantics = frozenset({"dot_date_recognition"})
    requires_features = frozenset()

    def matches(self, notation: DateNotation, contract: Contract) -> bool:
        """Accept valid calendar dates."""
        try:
            datetime(int(notation.N1), int(notation.N2), int(notation.N3))
            return True
        except ValueError:
            return False

    def normalize(self, notation: DateNotation, contract: Contract) -> str:
        """Normalize to ISO YYYY-MM-DD."""
        return f"{int(notation.N1):04d}-{int(notation.N2):02d}-{int(notation.N3):02d}"


class SecondDateRule(Rule[DateNotation]):
    """Second community rule: normalizes to day-first (distinct canonical value)."""

    name = "second_date_rule"
    strategy = RuleStrategy.PARSER
    provenance = PUBLICATION
    citation = "community test double"
    target_semantics = frozenset({"second_recognition"})
    requires_features = frozenset()

    def matches(self, notation: DateNotation, contract: Contract) -> bool:
        """Accept valid calendar dates."""
        try:
            datetime(int(notation.N1), int(notation.N2), int(notation.N3))
            return True
        except ValueError:
            return False

    def normalize(self, notation: DateNotation, contract: Contract) -> str:
        """Normalize to day-first DD-MM-YYYY."""
        return f"{int(notation.N3):02d}-{int(notation.N2):02d}-{int(notation.N1):04d}"


class CommunityISO8601Rule(Rule[DateNotation]):
    """Community rule targeting the shipped ``iso8601_recognition`` grammar."""

    name = "community_iso8601_rule"
    strategy = RuleStrategy.PARSER
    provenance = PUBLICATION
    citation = "community test double"
    target_semantics = frozenset({"iso8601_calendar_date"})
    requires_features = frozenset()

    def matches(self, notation: DateNotation, contract: Contract) -> bool:
        """Docstring-only method."""

        return True

    def normalize(self, notation: DateNotation, contract: Contract) -> str:
        """Normalize to a distinctive value if this rule ever runs."""
        return "0000-00-00"


class DanglingDateRule(Rule[DateNotation]):
    """Community rule whose target_semantics references a semantics id that
    no grammar claims."""

    name = "dangling_date_rule"
    strategy = RuleStrategy.PARSER
    provenance = PUBLICATION
    citation = "community test double"
    target_semantics = frozenset({"no_such_grammar"})
    requires_features = frozenset()

    def matches(self, notation: DateNotation, contract: Contract) -> bool:
        return True

    def normalize(self, notation: DateNotation, contract: Contract) -> str:
        return ""


# --- Fixtures ---


@pytest.fixture(autouse=True)
def _clean_registry() -> Iterator[None]:
    """Reset capability and extension registries before every test."""
    reset_registry()
    reset_extensions()
    yield
    reset_registry()
    reset_extensions()


@pytest.fixture(autouse=True)
def _register_extensions() -> Iterator[None]:
    """Register the Date capability plus the dot-date extension pair."""
    register_capability(DateCapability())
    register_grammar("date", DotDateGrammar)
    register_rule("date", DotDateRule)
    yield


# --- Tests ---


class TestCommunityGrammarOptIn:
    @pytest.mark.integration
    def test_opt_in_runs_community_grammar(self) -> None:
        """A grammar named in extra_grammars runs and resolves."""
        contract = DateContract(extra_grammars=("dot_date_recognition",))
        result = run_capability("2024.01.01", contract)
        assert result.status == Resolution.SUCCESS
        assert result.canonicalized_value == "2024-01-01"
        assert result.candidates[0].recognition_rule == "dot_date_recognition"
        assert result.candidates[0].validation_rule == "dot_date_rule"

    @pytest.mark.integration
    def test_not_opted_in_is_missing(self) -> None:
        """A registered but un-opted-in grammar never runs."""
        contract = DateContract()
        result = run_capability("2024.01.01", contract)
        assert result.status == Resolution.MISSING

    @pytest.mark.integration
    def test_unknown_extra_grammars_name_silently_skipped(self) -> None:
        """Naming an uninstalled grammar must not raise — treated as absent."""
        contract = DateContract(extra_grammars=("no_such_grammar",))
        result = run_capability("2024.01.01", contract)
        assert result.status == Resolution.MISSING

    @pytest.mark.integration
    def test_duplicate_extra_grammars_entries_deduped(self) -> None:
        """Listing the same grammar twice in extra_grammars runs it once."""
        contract = DateContract(
            extra_grammars=("dot_date_recognition", "dot_date_recognition")
        )
        result = run_capability("2024.01.01", contract)
        assert result.status == Resolution.SUCCESS
        assert result.canonicalized_value == "2024-01-01"
        assert len(result.candidates) == 1


class TestCompositionGuards:
    @pytest.mark.integration
    def test_community_grammar_collision_with_shipped_raises(self) -> None:
        """A community grammar name colliding with a shipped one fails fast."""
        register_grammar("date", ClashingDateGrammar)
        contract = DateContract(extra_grammars=("dot_date_recognition",))
        with pytest.raises(CapabilityError, match="Duplicate grammar"):
            run_capability("2024.01.01", contract)

    @pytest.mark.integration
    def test_community_rule_dangling_target_raises(self) -> None:
        """An opted-in community rule naming a missing semantics fails fast."""
        register_rule("date", DanglingDateRule)
        contract = DateContract(
            extra_grammars=("dot_date_recognition", "no_such_grammar")
        )
        with pytest.raises(ContractError, match="unknown semantics"):
            run_capability("2024.01.01", contract)

    @pytest.mark.integration
    def test_registration_after_canonicalize_raises(self) -> None:
        """Extension registries freeze with the first pipeline run."""
        contract = DateContract(extra_grammars=("dot_date_recognition",))
        run_capability("2024.01.01", contract)
        with pytest.raises(CapabilityError, match="frozen"):
            register_grammar("date", SecondDateGrammar)


class TestRecognitionOrdering:
    @pytest.mark.integration
    def test_community_grammars_activate_in_extra_order(self) -> None:
        """Two community grammars on the same span resolve in extra_grammars order."""
        register_grammar("date", SecondDateGrammar)
        register_rule("date", SecondDateRule)
        contract = DateContract(
            extra_grammars=("dot_date_recognition", "second_recognition")
        )
        result = run_capability("2024.01.01", contract)
        assert result.status == Resolution.AMBIGUOUS
        assert result.candidates[0].recognition_rule == "dot_date_recognition"
        assert result.candidates[1].recognition_rule == "second_recognition"
        assert result.candidates[0].value == "2024-01-01"
        assert result.candidates[1].value == "01-01-2024"

    @pytest.mark.integration
    def test_shipped_grammar_in_extra_is_deduped(self) -> None:
        """A shipped grammar also named in extra_grammars runs once (shipped slot)."""
        contract = DateContract(extra_grammars=("date_recognition",))
        result = run_capability("2026-01-15", contract)
        assert result.status == Resolution.SUCCESS
        assert result.canonicalized_value == "2026-01-15"
        assert len(result.candidates) == 1
        assert result.candidates[0].recognition_rule == "iso8601_recognition"

    @pytest.mark.integration
    def test_opt_in_ordering_shipped_first(self) -> None:
        """Shipped grammars keep their active_grammars slots before extras."""
        contract = DateContract(extra_grammars=("dot_date_recognition",))
        result = run_capability("2026-01-15 2024.01.01", contract)
        assert result.status == Resolution.AMBIGUOUS
        assert result.candidates[0].recognition_rule == "iso8601_recognition"
        assert result.candidates[1].recognition_rule == "dot_date_recognition"


class TestCommunityRuleOptIn:
    @pytest.mark.integration
    def test_community_rule_on_shipped_grammar_requires_activation(self) -> None:
        """A community rule targeting a shipped grammar is inert until opted in."""
        register_rule("date", CommunityISO8601Rule)

        default_result = run_capability("2026-01-15", DateContract())
        assert default_result.status == Resolution.SUCCESS
        assert default_result.canonicalized_value == "2026-01-15"
        assert not any(
            c.validation_rule == "community_iso8601_rule"
            for c in default_result.candidates
        )

        opted_in = DateContract(extra_grammars=("iso8601_recognition",))
        activated_result = run_capability("2026-01-15", opted_in)
        assert any(
            c.validation_rule == "community_iso8601_rule"
            for c in activated_result.candidates
        )

    @pytest.mark.integration
    def test_rule_opt_in_via_raw_semantics_id_without_grammar(self) -> None:
        """A raw semantics id in ``extra_grammars`` activates rules targeting it
        without opting in any community grammar.

        Locks the README-documented raw-name fallback
        (``semantics_by_name.get(n, n)``): ``iso8601_calendar_date`` is a
        known semantics id but not a grammar name, so the community rule
        targeting it fires on shipped ISO recognitions while no community
        grammar is activated (fail-fast ``ContractError`` applies only to ids
        no grammar claims).
        """
        register_rule("date", CommunityISO8601Rule)

        result = run_capability(
            "2026-01-15", DateContract(extra_grammars=("iso8601_calendar_date",))
        )
        assert any(
            c.validation_rule == "community_iso8601_rule" for c in result.candidates
        )
        assert all(
            c.recognition_rule == "iso8601_recognition" for c in result.candidates
        )
