"""RED golden vectors — ISSN/IBAN label glued policies (ADR 9.7).

Captured from legacy PipelineGrammar RegexStage before kernel migration.
ISSN uses glued allow with separator allow; IBAN uses glued reject.
Vectors must be byte-identical after migrating to LabelMatcher.
"""

from __future__ import annotations

import pytest

from paxman.capabilities.IBAN.grammar.iban_recognition import IBANRecognitionGrammar
from paxman.capabilities.ISSN.grammar.issn_recognition import ISSNRecognitionGrammar
from paxman.core.grammar import AnchorSet, BoundarySpec
from paxman.core.grammar.matchers.label import LabelMatcher
from paxman.core.grammar.scan_context import ScanContext

pytestmark = [pytest.mark.property]

# Golden vectors captured 2026-08-27 from legacy ISSNRecognitionGrammar
ISSN_GOLDEN = [
    ("0317-8471", [(0, 9, "03178471")]),
    ("03178471", [(0, 8, "03178471")]),
    ("ISSN 0317-8471", [(0, 14, "03178471")]),
    ("ISSN: 0317-8471", [(0, 15, "03178471")]),
    ("ISSN03178471", [(0, 12, "03178471")]),  # glued allow
    ("ISSN-L 0264-2875", [(0, 16, "02642875")]),
    ("ISSN-H 1365-201X", [(0, 16, "1365201X")]),
    ("issn 1050-124x", [(0, 14, "1050124X")]),
    ("see ISSN 0317-8471 (print)", [(4, 18, "03178471")]),
    ("0317-8471 0378-5955", [(0, 9, "03178471"), (10, 19, "03785955")]),
    ("912345679", []),
    ("1234-5679a", []),
    ("a0317-8471", []),
]

IBAN_GOLDEN = [
    ("DE89370400440532013000", [(0, 22, "DE89370400440532013000")]),
    ("DE89 3704 0044 0532 0130 00", [(0, 27, "DE89370400440532013000")]),
    ("IBAN: DE89 3704 0044 0532 0130 00", [(0, 33, "DE89370400440532013000")]),
    ("IBAN DE89370400440532013000", [(0, 27, "DE89370400440532013000")]),
    ("IBANDE89370400440532013000", []),  # glued reject
    ("XDE89370400440532013000", []),
    ("DE89370400440532013000Y", [(0, 23, "DE89370400440532013000Y")]),
    ("Pay to DE89 3704 0044 0532 0130 00 now", [(7, 34, "DE89370400440532013000")]),
]


def _issn_spans(text: str) -> list[tuple[int, int, str]]:
    g = ISSNRecognitionGrammar()
    return [(m.start, m.end, m.notation.digits) for m in g.recognize(text)]


def _iban_spans(text: str) -> list[tuple[int, int, str]]:
    g = IBANRecognitionGrammar()
    return [(m.start, m.end, m.notation.compact) for m in g.recognize(text)]


@pytest.mark.parametrize("text,expected", ISSN_GOLDEN)
def test_issn_golden_vectors(text: str, expected: list[tuple[int, int, str]]) -> None:
    assert _issn_spans(text) == expected


@pytest.mark.parametrize("text,expected", IBAN_GOLDEN)
def test_iban_golden_vectors(text: str, expected: list[tuple[int, int, str]]) -> None:
    assert _iban_spans(text) == expected


def test_label_glued_policy_table() -> None:
    """Glued-policy distinction ISSN allow vs IBAN reject (ADR §9.7 Table)."""
    reject = LabelMatcher(
        labels=frozenset({"IBAN"}), separator=r"[\s:-]+", glued_policy="reject"
    )
    allow = LabelMatcher(
        labels=frozenset({"ISSN"}), separator=r"[\s:-]*", glued_policy="allow"
    )
    assert reject.matches_prefix("IBANDE89") is False
    assert reject.matches_prefix("IBAN DE89") is True
    assert reject.matches_prefix("IBAN:DE89") is True
    assert allow.matches_prefix("ISSN03178471") is True
    assert allow.matches_prefix("ISSN 0317") is True
    assert allow.matches_prefix("ISSN") is False  # no rest


def test_label_matcher_match_not_raises() -> None:
    """LabelMatcher.match must be implemented (not NotImplementedError)."""
    # ISSN allow: glued glued variant must yield span
    allow_matcher = LabelMatcher(
        labels=frozenset({"ISSN"}),
        separator=r"[\s:-]*",
        glued_policy="allow",
        pattern=r"\d{4}-?\d{3}[0-9Xx]",
        flags=0,
        boundary=BoundarySpec.WORD,
        anchors=AnchorSet(),
        emit=lambda span, ctx: ctx.text[span[0] : span[1]],
    )
    view = ScanContext.of("ISSN03178471").view("__orig__", lambda t: (t, None, None))
    spans = allow_matcher.match(view)
    assert spans == [(0, 12)]

    reject_matcher = LabelMatcher(
        labels=frozenset({"IBAN"}),
        separator=r"[\s:-]+",
        glued_policy="reject",
        pattern=r"[A-Z]{2}[0-9]{2}[A-Z0-9]{11,30}",
        flags=0,
        boundary=BoundarySpec.WORD,
        anchors=AnchorSet(),
        emit=lambda span, ctx: ctx.text[span[0] : span[1]],
    )
    view2 = ScanContext.of("IBANDE89TEST").view("__orig__", lambda t: (t, None, None))
    spans2 = reject_matcher.match(view2)
    # glued reject must not produce a span at 0; bare core blocked by word guard at 4
    assert spans2 == []
