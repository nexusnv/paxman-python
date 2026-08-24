"""Candidates + label unit tests."""

from paxman.core.grammar.matchers.candidates import CandidatesMatcher
from paxman.core.grammar.matchers.label import LabelMatcher


def test_label_glued_policy_reject_vs_allow() -> None:
    reject = LabelMatcher(
        labels=frozenset({"IBAN"}), separator=r"[\s:-]+", glued_policy="reject"
    )
    allow = LabelMatcher(
        labels=frozenset({"ISSN"}), separator=r"[\s:-]*", glued_policy="allow"
    )
    assert reject.matches_prefix("IBANDE89") is False
    assert allow.matches_prefix("ISSN03178471") is True


def test_candidates_strategy_first_vs_all() -> None:
    c_all = CandidatesMatcher(candidates=("a", "b"), strategy="all")
    c_first = CandidatesMatcher(candidates=("a", "b"), strategy="first")
    assert c_all.strategy == "all"
    assert c_first.strategy == "first"
