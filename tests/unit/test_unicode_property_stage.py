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
    # Boundary values for Sc ranges
    assert stage.matches(chr(0x00A2))  # ¢ start of 00A2-00A5
    assert stage.matches(chr(0x00A5))  # ¥ end
    assert not stage.matches(chr(0x00A6))  # just after
    assert stage.matches(chr(0x20AC))  # € in 20A8-20BF


def test_unicode_property_stage_han():
    """Han property must match Han chars, not Latin."""
    stage = UnicodePropertyStage(property_name="Han", ranges=HAN_RANGES)
    assert stage.matches("中")  # U+4E2D Han
    assert stage.matches(chr(0x20000))  # supplementary Han
    assert not stage.matches("A")
    assert not stage.matches("$")


def test_unicode_property_stage_run_pipeline():
    """UnicodePropertyStage.run must append matches and preserve state."""
    from paxman.core.grammar.stages import PipelineState

    stage = UnicodePropertyStage(
        property_name="Sc",
        ranges=SC_RANGES,
        notation_fn=lambda token: token.upper(),
    )
    state = PipelineState(text="Pay $ and €", matches=[], scratch={"x": 1})
    result = stage.run(state)
    assert result.text == "Pay $ and €"
    assert result.scratch == {"x": 1}
    assert len(result.matches) == 2
    assert result.matches[0].raw_text == "$" and result.matches[0].start == 4
    assert result.matches[1].raw_text == "€"
    # supplementary Han offset
    han_stage = UnicodePropertyStage(
        property_name="Han", ranges=HAN_RANGES, notation_fn=lambda t: t
    )
    state2 = PipelineState(text="a\U00020000b", matches=[], scratch={})
    result2 = han_stage.run(state2)
    assert len(result2.matches) == 1
    assert result2.matches[0].raw_text == chr(0x20000)
    assert result2.matches[0].start == 1 and result2.matches[0].end == 2
    assert state2.text[result2.matches[0].start : result2.matches[0].end] == chr(
        0x20000
    )
