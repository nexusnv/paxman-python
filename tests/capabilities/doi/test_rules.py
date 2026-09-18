"""Tests for DOI rules (ISO 26324:2025, structure only)."""

from __future__ import annotations

import pathlib
from types import SimpleNamespace
from typing import cast

import pytest

from paxman.capabilities.DOI.contract import DOIContract
from paxman.capabilities.DOI.notation import DOINotation
from paxman.capabilities.DOI.rules.iso_26324_ed2025 import (
    PUBLICATION,
    Section4DOISyntax,
)
from paxman.core.domain import RuleStrategy

pytestmark = [pytest.mark.capability]

VALID = [
    ("10.1038", "nature12345"),
    ("10.1000", "182"),
    ("10.13003", "5jchdy"),
    ("10.7774", "cevr.2016.5.1.19"),
    ("10.5594", "smpte.st2067-21.2020"),
    ("10.1038", "a%2fb"),
    ("10.1234", "456ABC/zyz"),  # Handbook §6.3.1 multi-slash shape, valid prefix
]


def _notation(prefix: str, suffix: str) -> DOINotation:
    return DOINotation(prefix=prefix, suffix=suffix, canonical=f"{prefix}/{suffix}")


class TestSection4DOISyntax:
    """Prefix shape + '/' + non-empty quoteless suffix; no checksum."""

    def test_valid_structures(self) -> None:
        rule = Section4DOISyntax()
        contract = DOIContract()
        for prefix, suffix in VALID:
            assert rule.matches(_notation(prefix, suffix), contract) is True

    def test_bad_prefix_rejects(self) -> None:
        rule = Section4DOISyntax()
        contract = DOIContract()
        for prefix, suffix in (
            ("20.500.1234", "abc"),  # non-10. directory
            ("10.1234567890", "x"),  # registrant too long
            ("10.103", "x"),  # registrant too short
        ):
            assert rule.matches(_notation(prefix, suffix), contract) is False, prefix

    def test_empty_suffix_rejects(self) -> None:
        rule = Section4DOISyntax()
        contract = DOIContract()
        assert rule.matches(_notation("10.1038", ""), contract) is False

    def test_quoted_suffix_rejects(self) -> None:
        rule = Section4DOISyntax()
        contract = DOIContract()
        for suffix in ('a"b', "a'b", "a&b", "a b", "a\tb"):
            assert rule.matches(_notation("10.1038", suffix), contract) is False

    def test_nonprintable_suffix_rejects(self) -> None:
        # Graphic-type only (Handbook §4.3.1): Cc/Cf controls rejected.
        rule = Section4DOISyntax()
        contract = DOIContract()
        for suffix in ("a\x00b", "a\u200bb", "a\u200eb"):
            assert rule.matches(_notation("10.1038", suffix), contract) is False

    def test_printable_unicode_accepts(self) -> None:
        rule = Section4DOISyntax()
        contract = DOIContract()
        for suffix in ("café", "日本語", "\U0001f600"):
            assert rule.matches(_notation("10.1038", suffix), contract) is True

    def test_eidr_suffix_accepted_unvalidated(self) -> None:
        # Per-application checksums (Handbook §4.3.5, e.g. EIDR's
        # suffix-only check char) are accepted structurally and never
        # validated: the DOI system itself has no check digits.
        rule = Section4DOISyntax()
        contract = DOIContract()
        assert (
            rule.matches(_notation("10.5240", "B1FA-0EEC-C316-3316-3A73-L"), contract)
            is True
        )

    def test_normalize_exact_ascii_bare(self) -> None:
        rule = Section4DOISyntax()
        contract = DOIContract()
        assert (
            rule.normalize(_notation("10.1038", "nature12345"), contract)
            == "10.1038/nature12345"
        )

    def test_provenance_attrs(self) -> None:
        assert PUBLICATION.authority == "ISO"
        assert PUBLICATION.specification_name == "ISO 26324"
        assert PUBLICATION.version == "2025"
        assert PUBLICATION.lifecycle == "active"
        assert PUBLICATION.publication_year == 2025
        assert Section4DOISyntax().provenance is PUBLICATION

    def test_strategy_parser_six_attrs(self) -> None:
        rule = Section4DOISyntax()
        assert rule.strategy is RuleStrategy.PARSER
        assert rule.name == "Section 4-doi-syntax"
        assert rule.target_semantics == frozenset({"doi_recognition"})
        assert rule.requires_features == frozenset()
        assert rule.citation

    def test_matches_never_raises_on_malformed(self) -> None:
        rule = Section4DOISyntax()
        contract = DOIContract()
        bad = cast("DOINotation", SimpleNamespace(prefix=None, suffix=None))
        assert rule.matches(bad, contract) is False

    def test_normalize_never_raises_on_malformed(self) -> None:
        rule = Section4DOISyntax()
        contract = DOIContract()
        bad = cast("DOINotation", SimpleNamespace())
        assert rule.normalize(bad, contract) == ""

    def test_no_output_format_token(self) -> None:
        source = pathlib.Path(__file__).resolve().parent.parent.parent.parent / (
            "paxman/capabilities/DOI/rules/iso_26324_ed2025.py"
        )
        assert "output_format" not in source.read_text()
