import subprocess
import sys

import pytest

from paxman.capabilities.SIUnit.grammar.data.unit_symbol_tokens import SYMBOL_TOKENS
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


def test_si_hand_table_vs_sc_parity():
    """SI hand table for °µΩÅ must not be confused with Sc."""
    sc_set = {chr(cp) for start, end in SC_RANGES for cp in range(start, end + 1)}
    for sym in ["°", "µ", "Ω", "Å"]:
        assert sym in SYMBOL_TOKENS, f"{sym!r} missing from SI hand table"
        assert sym not in sc_set, f"{sym!r} should not be in Sc (Currency_Symbol)"


def test_han_vs_latin_parity():
    """Han property must be distinct from Latin hand table."""
    han_set = {chr(cp) for start, end in HAN_RANGES for cp in range(start, end + 1)}
    assert "中" in han_set
    assert chr(0x20000) in han_set  # supplementary Han U+20000
    assert "A" not in han_set
    assert "°" not in han_set
    han_stage = UnicodePropertyStage(property_name="Han", ranges=HAN_RANGES)
    assert han_stage.matches("中")
    assert han_stage.matches(chr(0x20000))
    assert not han_stage.matches("A")
    assert not han_stage.matches("°")


def test_sc_snapshot_correctness():
    """Sc snapshot must include U+058F and exclude U+0594 (CodeRabbit)."""
    stage = UnicodePropertyStage(property_name="Sc", ranges=SC_RANGES)
    assert stage.matches(chr(0x058F)), "U+058F Armenian Dram Sign should be Sc"
    assert not stage.matches(chr(0x0594)), "U+0594 Hebrew Accent should not be Sc"


def test_han_completeness():
    """Han snapshot must include every Unicode 15.1 Han range (CodeRabbit)."""
    stage = UnicodePropertyStage(property_name="Han", ranges=HAN_RANGES)
    # Previously missing ranges from U+2B820 through U+323AF — check Han
    # codepoints that are actually Han per Scripts.txt (not gaps)
    for cp in [0x2B820, 0x2CEB0, 0x30000, 0x323AF, 0x2F800, 0x3400, 0x4E00]:
        assert stage.matches(chr(cp)), f"U+{cp:04X} should be Han"
    # Gaps between Han blocks must not be Han
    for cp in [0x2CEAF, 0x2EBEF]:
        assert not stage.matches(chr(cp)), f"U+{cp:04X} should not be Han"
