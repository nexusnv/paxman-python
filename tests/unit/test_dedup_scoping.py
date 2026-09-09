"""Per-grammar keep_duplicate_spans scoping (ADR-0012 corollary 3, issue #71).

The ``keep_dup`` escape hatch used to be capability-wide: any grammar with a
``CandidatesMatcher(strategy="all")`` disabled span dedup for every
candidate. It is now per-grammar: only candidates whose source grammar opted
in skip dedup; every other grammar still dedups by
``(value, recognition_rule, validation_rule)``.
"""

from __future__ import annotations

import pytest

from paxman.capabilities.Date.capability import DateCapability
from paxman.capabilities.Date.contract import DateContract
from paxman.capabilities.Date.grammar.date_recognition import DateGrammar
from paxman.core.discovery import register_capability, reset_registry
from paxman.core.domain import (
    Candidate,
    Grammar,
    GrammarRule,
    RecognitionMatch,
    RecognizedRep,
    Resolution,
)
from paxman.core.grammar.anchors import AnchorSet
from paxman.core.grammar.matchers.candidates import CandidatesMatcher
from paxman.core.grammar.matchers.regex import RegexMatcher
from paxman.engine.orchestrator import (
    _dedup_candidates,
    _determine_status,
    _keep_duplicate_span_grammars,
    run_capability,
)

pytestmark = pytest.mark.unit

TEXT = "01/02/2026"

_FIRST_CANDIDATES = CandidatesMatcher(
    candidates=(
        RegexMatcher(
            pattern=r"(\d{1,2})/(\d{1,2})/(\d{4})",
            anchors=AnchorSet(),
        ),
        RegexMatcher(
            pattern=r"(\d{1,2})/(\d{1,2})/(\d{4})",
            anchors=AnchorSet(),
        ),
    ),
    strategy="first",
    candidate_names=("first_probe_a", "first_probe_b"),
    candidate_semantics=("first_probe_sem_a", "first_probe_sem_b"),
)


class _FirstProbeGrammar(Grammar[str]):
    """Minimal second grammar: CandidatesMatcher strategy="first"."""

    name = "first_probe_recognition"
    semantics = "first_probe_semantics"

    def __init__(self) -> None:
        self.matchers: tuple[CandidatesMatcher, ...] = (_FIRST_CANDIDATES,)

    def recognize(self, text: str) -> list[RecognitionMatch[str]]:
        return []


def _pair(
    grammar_name: str,
    value: str,
    rule_name: str,
    contract: DateContract,
    span: tuple[int, int] = (0, 10),
) -> tuple[Candidate, RecognizedRep[str]]:
    """Build one (Candidate, rep) pair attributed to ``grammar_name``."""
    candidate = Candidate(
        value=value,
        recognition_rule=grammar_name,
        validation_rule=rule_name,
        provenance=(),
        span=span,
    )
    rep: RecognizedRep[str] = RecognizedRep(
        notation=TEXT,
        contract=contract,
        grammar=GrammarRule(capability_name="date", grammar_name=grammar_name),
        start=span[0],
        end=span[1],
        raw_text=TEXT[span[0] : span[1]],
    )
    return (candidate, rep)


def _two_grammar_collection() -> list[tuple[Candidate, RecognizedRep[str]]]:
    """Shared span, duplicate-span candidates from an "all" and a "first" source."""
    contract = DateCapability.create_contract()
    return [
        _pair("us_recognition", "2026-01-02", "rule-a", contract),
        _pair("us_recognition", "2026-01-02", "rule-a", contract),
        _pair("first_probe_a", "X", "rule-a", contract),
        _pair("first_probe_a", "X", "rule-a", contract),
    ]


def test_duplicates_survive_only_for_opted_in_grammar() -> None:
    """The "all" grammar keeps duplicate spans; the "first" grammar dedups."""
    collected = _two_grammar_collection()
    deduped = _dedup_candidates(
        collected, keep_duplicate_spans_for=frozenset({"us_recognition"})
    )
    assert [(c.value, c.recognition_rule) for c in deduped] == [
        ("2026-01-02", "us_recognition"),
        ("2026-01-02", "us_recognition"),
        ("X", "first_probe_a"),
    ]
    assert _determine_status(deduped, True) is Resolution.AMBIGUOUS


def test_empty_opt_in_set_dedups_everything() -> None:
    """No opt-in behaves like the legacy dedup-everything path."""
    collected = _two_grammar_collection()
    deduped = _dedup_candidates(collected, keep_duplicate_spans_for=frozenset())
    assert [(c.value, c.recognition_rule) for c in deduped] == [
        ("2026-01-02", "us_recognition"),
        ("X", "first_probe_a"),
    ]


def test_opt_in_set_covers_grammar_and_candidate_names() -> None:
    """Date's "all" grammar opts in its candidate names; "first" opts out."""
    keep = _keep_duplicate_span_grammars([DateGrammar(), _FirstProbeGrammar()])
    assert "date_recognition" in keep
    assert {
        "iso8601_recognition",
        "us_recognition",
        "european_recognition",
        "slash_iso_recognition",
    } <= set(keep)
    assert "first_probe_recognition" not in keep
    assert "first_probe_a" not in keep
    assert "first_probe_b" not in keep


def test_no_opt_in_without_all_strategy() -> None:
    assert _keep_duplicate_span_grammars([_FirstProbeGrammar()]) == frozenset()


def test_date_slash_ambiguous_parity() -> None:
    """Date ``01/02/2026`` still yields the same four AMBIGUOUS candidates."""
    reset_registry()
    try:
        register_capability(DateCapability())
        result = run_capability(TEXT, DateCapability.create_contract())
    finally:
        reset_registry()
    assert result.status is Resolution.AMBIGUOUS
    assert sorted(
        (c.value, c.recognition_rule, c.validation_rule, c.span)
        for c in result.candidates
    ) == sorted(
        [
            ("2026-01-02", "us_recognition", "Derived-US-date-format", (0, 10)),
            ("2026-02-01", "us_recognition", "Derived-European-date-format", (0, 10)),
            ("2026-01-02", "european_recognition", "Derived-US-date-format", (0, 10)),
            (
                "2026-02-01",
                "european_recognition",
                "Derived-European-date-format",
                (0, 10),
            ),
        ]
    )
