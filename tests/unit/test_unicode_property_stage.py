import subprocess
import sys

import pytest

from paxman.core.grammar.data.unicode_ranges import HAN_RANGES, SC_RANGES
from paxman.core.grammar.stages import UnicodePropertyStage

pytestmark = pytest.mark.unit


def test_unicode_property_data_is_fresh():
    """Generated unicode_ranges.py must match checked-in snapshot."""
    result = subprocess.run(
        [sys.executable, "tools/regenerate_unicode_property_data.py", "--check"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_unicode_property_stage_matches_sc():
    """UnicodePropertyStage for Sc must match Currency_Symbol chars."""
    stage = UnicodePropertyStage(property_name="Sc", ranges=SC_RANGES)
    assert stage.matches("$")
    assert stage.matches("€")
    assert stage.matches(chr(0x20B9))  # ₹ U+20B9 BMP
    assert not stage.matches("A")
    assert not stage.matches("µ")  # not Sc
    assert not stage.matches("中")  # Han, not Sc


def test_unicode_property_stage_han():
    """Han property must match Han chars, not Latin."""
    stage = UnicodePropertyStage(property_name="Han", ranges=HAN_RANGES)
    assert stage.matches("中")  # U+4E2D Han
    assert stage.matches(chr(0x20000))  # supplementary Han
    assert not stage.matches("A")
    assert not stage.matches("$")
