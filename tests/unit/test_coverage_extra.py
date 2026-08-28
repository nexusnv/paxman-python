"""Extra coverage for deferred matchers and discovery.

Covers branches that are 0% in 0.2.0 because the matchers are not yet on
the kernel path (property/regex/scanner) and the scanner fingerprint path
in discovery. Also covers the lazy capabilities module shadowing logic.
"""

from __future__ import annotations

import pytest

from paxman.core.discovery import (
    freeze_registry,
    get_recognition_revision,
    register_capability,
    reset_registry,
)
from paxman.core.grammar.boundary_spec import BoundarySpec
from paxman.core.grammar.matchers.regex import RegexMatcher
from paxman.core.grammar.matchers.scanner import ScannerMatcher
from paxman.core.grammar.scan_context import View


def test_regex_matcher_match_and_boundary() -> None:
    m = RegexMatcher(pattern=r"\d+", boundary=BoundarySpec.WORD)
    view = View(
        subject="a 123 b 456", source_starts=None, source_ends=None, _text_len=11
    )
    spans = m.match(view)
    assert (2, 5) in spans
    assert (8, 11) in spans

    # Without boundary, also finds inside word
    m2 = RegexMatcher(pattern=r"\d+")
    view2 = View(subject="a1b2", source_starts=None, source_ends=None, _text_len=4)
    spans2 = m2.match(view2)
    assert (1, 2) in spans2
    assert (3, 4) in spans2

    # Invalid pattern raises ValueError
    with pytest.raises(ValueError, match="Invalid regex pattern"):
        RegexMatcher(pattern=r"[", flags=0)


def test_scanner_matcher_match_and_boundary() -> None:
    def scan_fn(view: View, pos: int) -> tuple[int, str] | None:
        # Simple scanner that matches "foo" at pos
        subj = view.subject
        if subj[pos:].startswith("foo"):
            return (pos + 3, "FOO")
        return None

    m = ScannerMatcher(scan=scan_fn, boundary=BoundarySpec.WORD, max_window=10)
    view = View(
        subject=" foo bar foo", source_starts=None, source_ends=None, _text_len=12
    )
    spans = m.match(view)
    # Should find "foo" at word boundaries
    assert len(spans) >= 1
    assert (1, 4) in spans

    # Max window exceeded — should be treated as miss (pos+1)
    m2 = ScannerMatcher(scan=scan_fn, max_window=2)
    # "foo" is length 3, exceeds max_window 2, so should not be emitted
    spans2 = m2.match(
        View(subject="foo", source_starts=None, source_ends=None, _text_len=3)
    )
    assert spans2 == []


def test_discovery_scanner_fingerprint_path() -> None:
    # Exercise the scanner fingerprint branch in freeze_registry that is
    # otherwise not covered because no shipped grammar uses ScannerMatcher
    # on the kernel path yet. We register a dummy capability with a ScannerMatcher.
    from paxman.core.capability import Capability
    from paxman.core.domain import Grammar, RecognitionMatch

    class DummyNotation:
        pass

    class DummyGrammar(Grammar[DummyNotation]):  # type: ignore[type-abstract]
        name = "dummy_scanner_grammar"
        semantics = "dummy"

        def __init__(self) -> None:
            # Create a ScannerMatcher with a scan fn and max_window
            def my_scan(view: View, pos: int) -> tuple[int, DummyNotation] | None:
                return None

            self.matchers = (ScannerMatcher(scan=my_scan, max_window=5),)  # type: ignore[attr-defined]

        def recognize(self, text: str) -> list[RecognitionMatch[DummyNotation]]:
            return []

    class DummyCapability(Capability[DummyNotation]):
        name = "dummy_scanner_cap"

        def get_grammars(self) -> list[Grammar[DummyNotation]]:  # type: ignore[override]
            return [DummyGrammar()]

        def get_rules(self) -> list[object]:  # type: ignore[override]
            return []

        def format_value(self, value: object, contract: object) -> str:  # type: ignore[override]
            return str(value)

    reset_registry()
    try:
        register_capability(DummyCapability())
        freeze_registry()
        rev = get_recognition_revision()
        assert isinstance(rev, str)
        assert len(rev) == 12 or rev == "0"
    finally:
        reset_registry()


def test_capabilities_lazy_import_shadowing() -> None:
    # Exercise the custom _CapabilitiesModule shadowing logic that is
    # otherwise at 70% (missed lines 78,82,95-101 etc.)
    import paxman.capabilities as cap_mod

    # Access via __getattr__ — should lazily import
    from paxman.capabilities import Country as CountryCap  # type: ignore[attr-defined]

    assert CountryCap is not None
    assert hasattr(CountryCap, "name")

    # Ensure the capability is already loaded, then check __dir__
    assert "Country" in dir(cap_mod)
    assert "Country" in cap_mod.__all__

    # Accessing a non-existent attribute should raise AttributeError
    with pytest.raises(AttributeError):
        cap_mod.__getattr__("NonExistentCapabilityXYZ")  # type: ignore[attr-defined]

    # Test __dir__ returns sorted __all__
    assert cap_mod.__dir__() == sorted(cap_mod.__all__)

    # Test the shadowing fix loop at bottom of file: ensure no leftover
    # globals that are modules with __path__ remain
    for name in cap_mod._LAZY:  # type: ignore[attr-defined]
        val = cap_mod.__dict__.get(name)
        if val is not None:
            assert not hasattr(val, "__path__") or isinstance(val, type)


def test_discovery_tokens_and_payload_branches() -> None:
    # Cover the tokens and payload branches in freeze_registry:
    # - tokens as frozenset
    # - payload repr
    # - TypeError for unsortable tokens
    from paxman.core.grammar.matchers.lexicon import LexiconMatcher

    reset_registry()
    try:
        from paxman.core.capability import Capability
        from paxman.core.domain import Grammar, RecognitionMatch

        class DummyLexiconGrammar(Grammar[str]):  # type: ignore[type-abstract]
            name = "dummy_lexicon"
            semantics = "dummy"

            def __init__(self) -> None:
                # Lexicon with tokens
                self.matchers = (LexiconMatcher(tokens=frozenset({"a", "b"})),)  # type: ignore[attr-defined]

            def recognize(self, text: str) -> list[RecognitionMatch[str]]:
                return []

        class DummyPayloadGrammar(Grammar[str]):  # type: ignore[type-abstract]
            name = "dummy_payload"
            semantics = "dummy2"

            def __init__(self) -> None:
                # Create a dummy matcher with payload but no tokens
                from dataclasses import dataclass

                from paxman.core.grammar.anchors import AnchorSet

                @dataclass(frozen=True)
                class PayloadMatcher:
                    payload = {"key": "value"}
                    kind = "test"
                    view = None
                    boundary = None
                    anchors = AnchorSet()
                    requires_features: frozenset[str] = frozenset()
                    _chosen = ""

                self.matchers = (PayloadMatcher(),)  # type: ignore[attr-defined]

            def recognize(self, text: str) -> list[RecognitionMatch[str]]:
                return []

        class DummyCap1(Capability[str]):
            name = "dummy_lex_cap"

            def get_grammars(self) -> list[Grammar[str]]:  # type: ignore[override]
                return [DummyLexiconGrammar()]

            def get_rules(self) -> list[object]:  # type: ignore[override]
                return []

            def format_value(self, value: object, contract: object) -> str:  # type: ignore[override]
                return str(value)

        class DummyCap2(Capability[str]):
            name = "dummy_payload_cap"

            def get_grammars(self) -> list[Grammar[str]]:  # type: ignore[override]
                return [DummyPayloadGrammar()]

            def get_rules(self) -> list[object]:  # type: ignore[override]
                return []

            def format_value(self, value: object, contract: object) -> str:  # type: ignore[override]
                return str(value)

        register_capability(DummyCap1())
        register_capability(DummyCap2())
        freeze_registry()
        rev = get_recognition_revision()
        assert isinstance(rev, str)
    finally:
        reset_registry()
