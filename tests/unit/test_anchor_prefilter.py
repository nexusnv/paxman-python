"""AnchorSet T0 prefilter — C-speed skip."""

from paxman.core.grammar.anchors import AnchorSet, HasDigit, LiteralAnchor
from paxman.core.grammar.scan_context import ScanContext


def test_literal_anchor_c_speed() -> None:
    a = AnchorSet(literals=frozenset({":"}), classes=(), key_sets=())
    assert a.passes("https://x", ScanContext.of("https://x")) is True
    assert a.passes("hello", ScanContext.of("hello")) is False
    b = LiteralAnchor(":").as_set()
    assert b.passes("https://x", ScanContext.of("https://x")) is True
    assert b.passes("hello", ScanContext.of("hello")) is False


def test_class_anchor_has_digit() -> None:
    a = HasDigit().as_set()
    assert a.passes("Phone +1 555", ScanContext.of("Phone +1 555")) is True
    assert a.passes("hello", ScanContext.of("hello")) is False


def test_key_set_anchor_word_start() -> None:
    from paxman.core.grammar.anchors import KeySetAnchor

    a = AnchorSet(literals=frozenset(), classes=(), key_sets=(frozenset({"U", "E"}),))
    assert a.passes("United States", ScanContext.of("United States")) is True
    assert a.passes("xyz", ScanContext.of("xyz")) is False
    b = KeySetAnchor(frozenset({"U", "E"})).as_set()
    assert b.passes("United States", ScanContext.of("United States")) is True
    assert b.passes("xyz", ScanContext.of("xyz")) is False


def test_anchor_empty_passes() -> None:
    a = AnchorSet(literals=frozenset(), classes=(), key_sets=())
    assert a.passes("anything", ScanContext.of("anything")) is True
