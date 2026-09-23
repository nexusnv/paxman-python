"""Tests for GTIN authority data tables."""

import pytest

from paxman.capabilities.GTIN.rules.data.gs1_prefix import (
    GS1_GTIN8_EXCEPTIONS,
    GS1_MO_RANGES,
)
from paxman.capabilities.GTIN.rules.data.verified_snapshot import ISSUED_GTINS


def _prefix_in_ranges(prefix: int) -> bool:
    return any(s <= prefix <= e for s, e, _ in GS1_MO_RANGES)


@pytest.mark.capability
class TestGTINData:
    def test_prefix_table_shape(self) -> None:
        # ranges sorted, non-overlapping, start <= end
        starts = [s for s, _, _ in GS1_MO_RANGES]
        assert starts == sorted(starts)
        for s, e, _ in GS1_MO_RANGES:
            assert s <= e
        # Adjacent-range check: zip pairs row i with row i+1, so the two
        # inputs are deliberately unequal in length (strict=False).
        pairs = zip(GS1_MO_RANGES, GS1_MO_RANGES[1:], strict=False)
        for (_, e1, _), (s2, _, _) in pairs:
            assert e1 < s2
        # 4-char GTIN-8 exceptions separate set
        assert all(len(x) == 4 and x.isdigit() for x in GS1_GTIN8_EXCEPTIONS)
        assert {"9620", "9621", "9622", "9623", "9624"} <= GS1_GTIN8_EXCEPTIONS

    def test_suite_prefixes_resolve(self) -> None:
        # Every pipeline SUCCESS vector's allocation key must resolve: the
        # zero-stripped view, EAN-13 view prepended for UPC-A (12-digit),
        # packaging indicator skipped for GTIN-14 (14-digit).
        for prefix in [19, 61, 206, 345, 501, 590, 629, 963, 978]:
            assert _prefix_in_ranges(prefix), prefix
        # 999 stays the miss fixture (990-999 excluded, see data header)
        assert not _prefix_in_ranges(999)
        # 614 (EAN-13 view) is genuinely unallocated — distinct from the
        # UPC-A flagship's key 061 (GS1 US), which does resolve.
        assert not _prefix_in_ranges(614)
        assert _prefix_in_ranges(61)

    def test_prefix_source_comments(self) -> None:
        import pathlib

        text = pathlib.Path(
            "paxman/capabilities/GTIN/rules/data/gs1_prefix.py"
        ).read_text()
        assert "REFRESH PROCEDURE" in text
        assert "gs1.org" in text
        # every MO row carries a comment (spot-check UK + UAE + Bookland)
        assert "GS1 UK" in text
        assert "GS1 UAE" in text
        assert "Bookland" in text
        # UPC-A keys the EAN-13 view (614... -> 061), documented in the header
        assert "EAN-13 view" in text
        # coupon rationale: 981-984 in (allocated), 990-999 out (999 miss)
        assert "990-999" in text
        # 000 reserved sub-range note
        assert "0001-0009" in text
        # no leftover drafting debris
        assert "622?" not in text

    def test_verified_snapshot_empty_shipped(self) -> None:
        assert frozenset() == ISSUED_GTINS
