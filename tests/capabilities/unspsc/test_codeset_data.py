"""Codeset snapshot data tests (Task 3).

The membership table is generated, never hand-edited:
paxman/shared_data/unspsc_snapshot.json --(tools/regenerate_unspsc_data.py)-->
paxman/capabilities/UNSPSC/rules/data/unspsc_codeset.py.
"""

from __future__ import annotations

import subprocess
import sys

import pytest

from paxman.capabilities.UNSPSC.rules.data.unspsc_codeset import (
    CODESET_VERSION,
    LIVE_STEMS,
)

KNOWN_LIVE = (
    "44103103",  # printer/facsimile toner
    "43211503",  # notebook computers
    "10101501",  # cats
    "25101703",  # ambulances
    "44121706",  # wooden pencils
    "43211602",  # docking stations
    "43000000",  # segment 43
    "43210000",  # family 4321
    "43211500",  # class 432115
)

KNOWN_ABSENT = (
    "44103199",  # well-formed, unissued (illustrative)
    "99999999",  # no segment 99
)


@pytest.mark.capability
class TestCodesetData:
    def test_version_pinned(self) -> None:
        assert isinstance(CODESET_VERSION, str) and CODESET_VERSION

    def test_covers_known_live_stems(self) -> None:
        for stem in KNOWN_LIVE:
            assert stem in LIVE_STEMS, stem

    def test_excludes_unissued(self) -> None:
        for stem in KNOWN_ABSENT:
            assert stem not in LIVE_STEMS, stem

    def test_all_stems_are_8_ascii_digits(self) -> None:
        assert len(LIVE_STEMS) > 10_000
        for stem in LIVE_STEMS:
            assert len(stem) == 8 and stem.isascii() and stem.isdigit(), stem

    def test_regenerate_check_is_clean(self) -> None:
        proc = subprocess.run(
            [sys.executable, "tools/regenerate_unspsc_data.py", "--check"],
            capture_output=True,
            text=True,
            cwd=".",
        )
        assert proc.returncode == 0, proc.stderr or proc.stdout
