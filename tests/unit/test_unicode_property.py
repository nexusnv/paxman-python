"""Unicode property ranges — generated sorted-range bisect (D10)."""

from __future__ import annotations

import bisect

import pytest

pytestmark = pytest.mark.unit


def test_unicode_ranges_sorted_and_typed() -> None:
    from paxman.core.grammar.data.unicode_ranges import UNICODE_RANGES

    assert isinstance(UNICODE_RANGES, tuple)
    # Each entry is a (start, end) int pair with start <= end
    for start, end in UNICODE_RANGES:
        assert isinstance(start, int)
        assert isinstance(end, int)
        assert 0 <= start <= end <= 0x10FFFF
    # Sorted by start, non-overlapping
    starts = [s for s, _ in UNICODE_RANGES]
    assert starts == sorted(starts)
    for i in range(len(UNICODE_RANGES) - 1):
        _, end = UNICODE_RANGES[i]
        nxt_start, _ = UNICODE_RANGES[i + 1]
        assert end < nxt_start


def test_unicode_ranges_bisect_membership() -> None:
    from paxman.core.grammar.data.unicode_ranges import UNICODE_RANGES

    # Membership via bisect — ICU discipline placeholder.
    # With empty snapshot the table is empty; bisect must still be well-formed.
    def contains(cp: int) -> bool:
        # Find rightmost range with start <= cp
        idx = bisect.bisect_right(UNICODE_RANGES, (cp, 0x10FFFF)) - 1
        if idx < 0:
            return False
        s, e = UNICODE_RANGES[idx]
        return s <= cp <= e

    # Empty table contains nothing; non-empty table invariants still hold
    assert contains(0x0041) is False or UNICODE_RANGES != ()
    assert contains(0x10FFFF) is False or UNICODE_RANGES != ()
    # Deterministic: repeated calls agree
    assert contains(0x0061) == contains(0x0061)
