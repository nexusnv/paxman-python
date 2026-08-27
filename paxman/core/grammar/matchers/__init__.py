"""Matcher kinds — re-export the 6 kernel matchers.

(regex/lexicon/scanner/combinator/candidates/label).
Property deleted per ADR-0009 §9."""

from __future__ import annotations

from paxman.core.grammar.matchers.candidates import CandidatesMatcher
from paxman.core.grammar.matchers.combinator import CombinatorMatcher
from paxman.core.grammar.matchers.label import LabelMatcher
from paxman.core.grammar.matchers.lexicon import LexiconMatcher
from paxman.core.grammar.matchers.regex import RegexMatcher
from paxman.core.grammar.matchers.scanner import ScannerMatcher

__all__ = [
    "CandidatesMatcher",
    "CombinatorMatcher",
    "LabelMatcher",
    "LexiconMatcher",
    "RegexMatcher",
    "ScannerMatcher",
]
