"""Recognition-layer pipeline internals (capability-agnostic)."""

from __future__ import annotations

from paxman.core.grammar.anchors import AnchorSet, HasDigit, KeySetAnchor, LiteralAnchor
from paxman.core.grammar.boundary import BoundaryGuard
from paxman.core.grammar.boundary_spec import BoundarySpec
from paxman.core.grammar.composer import AmountComposer
from paxman.core.grammar.engine_loop import _run_matchers
from paxman.core.grammar.lexicon import LexiconAlternation
from paxman.core.grammar.matcher_spec import EmitFn, MatcherKind, MatcherSpec
from paxman.core.grammar.matchers.candidates import CandidatesMatcher
from paxman.core.grammar.matchers.combinator import CombinatorMatcher
from paxman.core.grammar.matchers.label import LabelMatcher
from paxman.core.grammar.matchers.lexicon import LexiconMatcher
from paxman.core.grammar.matchers.regex import RegexMatcher
from paxman.core.grammar.matchers.scanner import ScannerMatcher
from paxman.core.grammar.normalizers import (
    AccentStrip,
    CaseFold,
    CountryNameFold,
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
    "CandidatesMatcher",
    "CaseFold",
    "CombinatorMatcher",
    "CountryNameFold",
    "EmitFn",
    "HasDigit",
    "IDNAFold",
    "KeySetAnchor",
    "LabelMatcher",
    "LexiconAlternation",
    "LexiconMatcher",
    "LexiconStage",
    "PipelineGrammar",
    "PipelineState",
    "PostStage",
    "RegexMatcher",
    "RegexStage",
    "ScanContext",
    "ScannerMatcher",
    "LiteralAnchor",
    "MatcherKind",
    "MatcherSpec",
    "Normalizer",
    "NormalizerSequence",
    "SeparatorFold",
    "Stage",
    "StandardPre",
    "StripSeparators",
    "SymbolFold",
    "View",
    "WholeInputLookup",
    "_run_matchers",
]
