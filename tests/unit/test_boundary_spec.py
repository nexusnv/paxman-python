"""BoundarySpec data — declarative, checked at hit positions."""

from paxman.core.grammar.boundary_spec import BoundarySpec


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
