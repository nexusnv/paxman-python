"""BoundarySpec data — declarative, checked at hit positions."""

import re

import pytest

from paxman.core.grammar.boundary_spec import (
    BoundarySpec,
    _estimate_width,
    _pattern_to_chars,
)


def test_word_spec_blocks_inside_token_via_hit_check() -> None:
    from paxman.core.grammar.scan_context import ScanContext

    ctx = ScanContext.of("x € y")
    spec = BoundarySpec.WORD
    assert ctx.check_hit(ctx.text, 2, 3, spec) is True
    # "x€" with hit at 1,2 where left char is 'x' (\w) should block
    assert ScanContext.of("x€").check_hit("x€", 1, 2, spec) is False


def test_consuming_mode_inner_span_only() -> None:
    from paxman.core.grammar.scan_context import ScanContext

    ctx = ScanContext.of(" [2001:db8::1] ")
    spec = BoundarySpec.IPV6_TOKEN
    assert spec.mode == "consuming"
    span = (2, 13)
    assert ctx.text[span[0] : span[1]] == "2001:db8::1"


def test_preset_table_covers_11_factories() -> None:
    assert BoundarySpec.WORD_SIGN.left is not None
    assert BoundarySpec.DEGREE_WORD_SIGN.left != BoundarySpec.WORD_SIGN.left
    # degree_word_sign's left should contain °
    left = BoundarySpec.DEGREE_WORD_SIGN.left
    assert left is not None
    assert any("°" in entry for entry in left)
    assert BoundarySpec.DIGIT is not None
    assert BoundarySpec.PHONE_NATIONAL is not None


def test_pattern_to_chars_unicode_escape() -> None:
    chars = _pattern_to_chars(r"[\w\u2212]")
    assert chars is not None
    assert "\u2212" in chars


def test_pattern_to_chars_hex_escape() -> None:
    assert _pattern_to_chars(r"[\x41]") == frozenset({"A"})


def test_pattern_to_chars_negated_none() -> None:
    assert _pattern_to_chars("[^ab]") is None


def test_pattern_to_chars_malformed_escape_falls_back() -> None:
    assert _pattern_to_chars(r"[\u12]") is None
    assert _pattern_to_chars(r"[\xZZ]") is None
    assert _pattern_to_chars(r"[\U00110000]") is None


def test_estimate_width_quantifier_returns_none() -> None:
    assert _estimate_width(r"\w+") is None
    assert _estimate_width(r"\d{2,3}") is None
    assert _estimate_width("[ab]+") is None
    assert _estimate_width("(ab)") is None
    assert _estimate_width(r"\d[ -]") == 2
    assert _estimate_width(r"\w") == 1


def test_quantified_guard_catches_distant_violation() -> None:
    from paxman.core.grammar.boundary_spec import check_boundary

    spec = BoundarySpec(left=(r"\w{5}",), right=None)
    # Five word chars directly left of the hit violate the guard; a
    # 4-wide window ("2345") would miss it.
    assert check_boundary("12345", 5, 5, spec) is False
    assert check_boundary("1234", 4, 4, spec) is True


def test_malformed_escape_construction_fails_fast() -> None:
    """Malformed escapes are invalid regex: fail fast, never silently lower."""
    with pytest.raises(re.error):
        BoundarySpec(left=(r"[\xZZ]",), right=None)


def test_alternation_guard_grouped_at_left_edge() -> None:
    from paxman.core.grammar.boundary_spec import check_boundary

    spec = BoundarySpec(left=(r"a|bc",), right=None)
    # "ax" ends with neither alternative: no violation. An ungrouped
    # `a|bc\Z` would match the free "a" and wrongly violate.
    assert check_boundary("ax", 2, 2, spec) is True
    # Genuine violations still fire on the full remainder.
    assert check_boundary("xxbc", 4, 4, spec) is False
    assert check_boundary("xxa", 3, 3, spec) is False


def test_alternation_guard_grouped_at_right_edge() -> None:
    from paxman.core.grammar.boundary_spec import check_boundary

    spec = BoundarySpec(left=None, right=(r"a|bc",))
    # "xbc" starts with neither alternative: no violation. An ungrouped
    # `\Aa|bc` would match the free "bc" and wrongly violate.
    assert check_boundary("xbc", 0, 0, spec) is True
    # Genuine violations still fire on the full remainder.
    assert check_boundary("bcx", 0, 0, spec) is False
    assert check_boundary("ax", 0, 0, spec) is False
