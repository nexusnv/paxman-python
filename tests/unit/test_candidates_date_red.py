"""RED: golden vectors for Date candidates migration (B4a).

Captures legacy Date recognitions before CandidatesMatcher lands;
fails while CandidatesMatcher is NotImplementedError, passes after.
"""

from __future__ import annotations

from paxman.capabilities.Date.grammar.european_recognition import EuropeanDateGrammar
from paxman.capabilities.Date.grammar.iso8601_recognition import ISO8601DateGrammar
from paxman.capabilities.Date.grammar.slash_iso_recognition import SlashISODateGrammar
from paxman.capabilities.Date.grammar.us_recognition import USDateGrammar
from paxman.core.grammar.anchors import AnchorSet
from paxman.core.grammar.boundary_spec import BoundarySpec
from paxman.core.grammar.matchers.candidates import CandidatesMatcher
from paxman.core.grammar.matchers.regex import RegexMatcher
from paxman.core.grammar.scan_context import ScanContext
from tests.property._legacy_remaining_grammars import (
    LegacyEuropeanDateGrammar,
    LegacyISO8601DateGrammar,
    LegacySlashISODateGrammar,
    LegacyUSDateGrammar,
)


def _legacy_vectors() -> list[tuple[str, list[tuple[int, int, str]]]]:
    """Golden vectors: text -> expected (start, end, raw) per legacy combined."""
    return [
        ("2026-01-15", [(0, 10, "2026-01-15")]),
        ("2026/01/15", [(0, 10, "2026/01/15")]),  # slash_iso
        (
            "01/02/2026",
            [(0, 10, "01/02/2026"), (0, 10, "01/02/2026")],
        ),  # us + european same span -> 2
        (
            "01/02/26 foo 01/02/2026",
            [
                (0, 8, "01/02/26"),
                (0, 8, "01/02/26"),
                (13, 23, "01/02/2026"),
                (13, 23, "01/02/2026"),
            ],
        ),
        ("2026-07-26 and 2025-12-31", [(0, 10, "2026-07-26"), (15, 25, "2025-12-31")]),
        ("", []),
        ("No dates here", []),
    ]


def test_candidates_matcher_all_keeps_ambiguous() -> None:
    """CandidatesMatcher all keeps both US and European spans for 01/02/2026."""
    iso = RegexMatcher(
        pattern=r"(\d{4})-(\d{2})-(\d{2})",
        boundary=BoundarySpec.DIGIT,
        view=None,
        anchors=AnchorSet(),
    )
    slash = RegexMatcher(
        pattern=r"(\d{4})/(\d{1,2})/(\d{1,2})",
        boundary=BoundarySpec.DIGIT,
        view=None,
        anchors=AnchorSet(),
    )
    us = RegexMatcher(
        pattern=r"(\d{1,2})/(\d{1,2})/(\d{4}|\d{2})",
        boundary=BoundarySpec.DIGIT,
        view=None,
        anchors=AnchorSet(),
    )
    eu = RegexMatcher(
        pattern=r"(\d{1,2})/(\d{1,2})/(\d{4}|\d{2})",
        boundary=BoundarySpec.DIGIT,
        view=None,
        anchors=AnchorSet(),
    )
    cm_all = CandidatesMatcher(candidates=(iso, slash, us, eu), strategy="all")
    view = ScanContext.of("01/02/2026").view("__orig__", lambda t: (t, None, None))
    spans = cm_all.match(view)
    # 'all' must keep both us and eu at same span -> 2 entries
    assert spans.count((0, 10)) == 2, f"expected 2 spans at (0,10) for all, got {spans}"


def test_candidates_matcher_first_wins_per_span() -> None:
    """CandidatesMatcher strategy='first' must deduplicate same span to 1."""
    us = RegexMatcher(
        pattern=r"(\d{1,2})/(\d{1,2})/(\d{4})",
        boundary=BoundarySpec.DIGIT,
        view=None,
        anchors=AnchorSet(),
    )
    eu = RegexMatcher(
        pattern=r"(\d{1,2})/(\d{1,2})/(\d{4})",
        boundary=BoundarySpec.DIGIT,
        view=None,
        anchors=AnchorSet(),
    )
    cm_first = CandidatesMatcher(candidates=(us, eu), strategy="first")
    view = ScanContext.of("01/02/2026").view("__orig__", lambda t: (t, None, None))
    spans = cm_first.match(view)
    assert spans.count((0, 10)) == 1


def test_legacy_date_golden_vectors() -> None:
    """Legacy combined recognitions for Date (4 grammars) — frozen RED vectors."""
    legacy_grammars = [
        LegacyISO8601DateGrammar(),
        LegacyUSDateGrammar(),
        LegacyEuropeanDateGrammar(),
        LegacySlashISODateGrammar(),
    ]
    # also check staged pipeline grammars match legacy for these vectors
    new_grammars = [
        ISO8601DateGrammar(),
        USDateGrammar(),
        EuropeanDateGrammar(),
        SlashISODateGrammar(),
    ]
    for text, expected in _legacy_vectors():
        legacy_matches = []
        for g in legacy_grammars:
            legacy_matches.extend(g.recognize(text))
        # sort as engine does: by start
        legacy_matches_sorted = sorted(legacy_matches, key=lambda m: (m.start, m.end))
        assert [
            (m.start, m.end, m.raw_text) for m in legacy_matches_sorted
        ] == expected, f"legacy mismatch for {text!r}"
        new_matches = []
        for g in new_grammars:
            new_matches.extend(g.recognize(text))
        new_sorted = sorted(new_matches, key=lambda m: (m.start, m.end))
        assert [(m.start, m.end, m.raw_text) for m in new_sorted] == expected
