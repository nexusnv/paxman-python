"""Recognition-layer pipeline internals (capability-agnostic)."""

from __future__ import annotations

from paxman.core.grammar.anchors import AnchorSet, HasDigit, KeySetAnchor, LiteralAnchor
from paxman.core.grammar.boundary import BoundaryGuard
from paxman.core.grammar.boundary_spec import BoundarySpec
from paxman.core.grammar.composer import AmountComposer
from paxman.core.grammar.lexicon import LexiconAlternation
from paxman.core.grammar.normalizers import (
    AccentStrip,
    CaseFold,
    IDNAFold,
    Normalizer,
    NormalizerSequence,
    SeparatorFold,
    StripSeparators,
    SymbolFold,
)
from paxman.core.grammar.pipeline import PipelineGrammar
from paxman.core.grammar.scan_context import ScanContext, View
from paxman.core.grammar.stages import (
    LexiconStage,
    PipelineState,
    PostStage,
    RegexStage,
    Stage,
    StandardPre,
    WholeInputLookup,
)

__all__ = [
    "AccentStrip",
    "AmountComposer",
    "AnchorSet",
    "BoundaryGuard",
    "BoundarySpec",
    "CaseFold",
    "HasDigit",
    "IDNAFold",
    "KeySetAnchor",
    "LexiconAlternation",
    "LexiconStage",
    "LiteralAnchor",
    "Normalizer",
    "NormalizerSequence",
    "PipelineGrammar",
    "PipelineState",
    "PostStage",
    "RegexStage",
    "ScanContext",
    "SeparatorFold",
    "Stage",
    "StandardPre",
    "StripSeparators",
    "SymbolFold",
    "View",
    "WholeInputLookup",
]
