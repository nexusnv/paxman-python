"""MatcherSpec data + requires_features omission + anchor+bondary wiring."""

from paxman.core.grammar.anchors import AnchorSet
from paxman.core.grammar.boundary_spec import BoundarySpec
from paxman.core.grammar.matcher_spec import MatcherSpec


def test_matcher_spec_is_data() -> None:
    spec = MatcherSpec(
        kind="regex",
        payload=r"\d{4}-\d{2}-\d{2}",
        view=None,
        boundary=BoundarySpec.DIGIT,
        anchors=AnchorSet(),
        emit=lambda span, ctx: span,
        requires_features=frozenset(),
    )
    assert spec.kind == "regex"
    assert spec.view is None
    assert spec.boundary == BoundarySpec.DIGIT


def test_requires_features_omission() -> None:
    spec = MatcherSpec(
        kind="regex",
        payload=r"foo",
        view=None,
        boundary=None,
        anchors=AnchorSet(),
        emit=lambda s, ctx: s,
        requires_features=frozenset({"include_ipv6"}),
    )
    assert spec.requires_features == frozenset({"include_ipv6"})


def test_view_selector() -> None:
    spec = MatcherSpec(
        kind="lexicon",
        payload=frozenset({"hello"}),
        view="casefolded",
        boundary=BoundarySpec.WORD,
        anchors=AnchorSet(),
        emit=lambda s, ctx: s,
    )
    assert spec.view == "casefolded"


def test_frozen_slots() -> None:
    MatcherSpec(
        kind="regex",
        payload="x",
        view=None,
        boundary=None,
        anchors=AnchorSet(),
        emit=lambda s, ctx: s,
    )
    assert hasattr(MatcherSpec, "__slots__")
    assert MatcherSpec.__dataclass_params__.frozen is True
