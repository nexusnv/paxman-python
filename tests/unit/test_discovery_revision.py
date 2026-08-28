"""RED→GREEN gate for Task A2: per-matcher digest memoization.

Asserts freeze_registry uses matcher.digest (computed once at construction)
instead of re-deriving sorted tokens per freeze, and that snapshot hashing
is memoized. Timing <5ms is recorded in PR body, not gating.
"""

from __future__ import annotations


def test_freeze_twice_identical_recognition_revision() -> None:
    from paxman.capabilities.Country.capability import CountryCapability
    from paxman.core.discovery import (
        freeze_registry,
        get_recognition_revision,
        register_capability,
        reset_registry,
    )

    reset_registry()
    register_capability(CountryCapability())
    freeze_registry()
    rev1 = get_recognition_revision()
    reset_registry()
    register_capability(CountryCapability())
    freeze_registry()
    rev2 = get_recognition_revision()
    assert rev1 == rev2, (
        f"freeze twice must give identical revision: {rev1!r} != {rev2!r}"
    )
    assert rev1 != "0"
    reset_registry()


def test_repeated_freeze_uses_cached_digests() -> None:
    """Second onward freeze must use cached digests via matcher.digest identity."""
    from paxman.core.discovery import (
        freeze_registry,
        reset_registry,
    )
    from paxman.core.grammar.matchers.lexicon import LexiconMatcher
    from paxman.core.grammar.matchers.regex import RegexMatcher
    from paxman.core.grammar.matchers.scanner import ScannerMatcher
    from paxman.core.grammar.scan_context import View

    lex = LexiconMatcher(tokens=frozenset({"hello", "world"}))
    assert hasattr(lex, "digest")
    lex_d = getattr(lex, "digest", None)
    assert isinstance(lex_d, str) and len(lex_d) > 0

    reg = RegexMatcher(pattern=r"\d+", flags=0)
    assert hasattr(reg, "digest")
    reg_d = getattr(reg, "digest", None)
    assert isinstance(reg_d, str) and len(reg_d) > 0

    def _scan(view: View, pos: int):  # type: ignore[no-untyped-def]
        return None

    scan = ScannerMatcher(scan=_scan, max_window=10)
    assert hasattr(scan, "digest")
    scan_d = getattr(scan, "digest", None)
    assert isinstance(scan_d, str) and len(scan_d) > 0

    lex_digest_id = id(lex_d)
    _ = (reg_d, scan_d)

    from paxman.capabilities.Country.capability import CountryCapability
    from paxman.core.discovery import register_capability

    for _ in range(5):
        reset_registry()
        register_capability(CountryCapability())
        freeze_registry()
        lex2 = LexiconMatcher(tokens=frozenset({"hello", "world"}))
        assert getattr(lex2, "digest", None) == getattr(lex, "digest", None), (
            "same tokens must give equal digest"
        )

    assert getattr(lex, "digest", None) == getattr(
        LexiconMatcher(tokens=frozenset({"hello", "world"})), "digest", None
    )
    # digest is computed once at construction, so the string object is retained
    assert id(getattr(lex, "digest", None)) == lex_digest_id

    for _ in range(3):
        assert hasattr(LexiconMatcher(tokens=frozenset({"a", "b"})), "digest")

    reset_registry()


def test_lexicon_digest_purity_same_tokens_equal() -> None:
    from paxman.core.grammar.matchers.lexicon import LexiconMatcher

    a = LexiconMatcher(tokens=frozenset({"alpha", "beta", "gamma"}))
    b = LexiconMatcher(tokens=frozenset({"gamma", "beta", "alpha"}))
    assert getattr(a, "digest", None) == getattr(b, "digest", None), (
        "same tokens in any order must give equal digest"
    )
    assert isinstance(getattr(a, "digest", None), str)


def test_lexicon_digest_changes_on_token_add() -> None:
    from paxman.core.grammar.matchers.lexicon import LexiconMatcher

    base = LexiconMatcher(tokens=frozenset({"alpha", "beta"}))
    plus_one = LexiconMatcher(tokens=frozenset({"alpha", "beta", "gamma"}))
    assert getattr(base, "digest", None) != getattr(plus_one, "digest", None), (
        "+1 token must change digest"
    )


def test_regex_digest_purity() -> None:
    from paxman.core.grammar.matchers.regex import RegexMatcher

    a = RegexMatcher(pattern=r"hello\d+", flags=0)
    b = RegexMatcher(pattern=r"hello\d+", flags=0)
    c = RegexMatcher(pattern=r"hello\d+", flags=2)
    d = RegexMatcher(pattern=r"world\d+", flags=0)
    assert getattr(a, "digest", None) == getattr(b, "digest", None)
    assert getattr(a, "digest", None) != getattr(c, "digest", None), (
        "flags change must change digest"
    )
    assert getattr(a, "digest", None) != getattr(d, "digest", None), (
        "pattern change must change digest"
    )


def test_scanner_digest_purity() -> None:
    from paxman.core.grammar.boundary_spec import BoundarySpec
    from paxman.core.grammar.matchers.scanner import ScannerMatcher
    from paxman.core.grammar.scan_context import View

    def _scan_a(view: View, pos: int):  # type: ignore[no-untyped-def]
        return None

    def _scan_b(view: View, pos: int):  # type: ignore[no-untyped-def]
        return None

    s1 = ScannerMatcher(scan=_scan_a, max_window=10)
    s2 = ScannerMatcher(scan=_scan_a, max_window=10)
    s3 = ScannerMatcher(scan=_scan_a, max_window=20)
    s4 = ScannerMatcher(scan=_scan_b, max_window=10)
    assert getattr(s1, "digest", None) == getattr(s2, "digest", None)
    assert getattr(s1, "digest", None) != getattr(s3, "digest", None), (
        "max_window change must change digest"
    )
    assert getattr(s1, "digest", None) != getattr(s4, "digest", None), (
        "qualname change must change digest"
    )

    s5 = ScannerMatcher(scan=_scan_a, max_window=10, boundary=BoundarySpec.WORD)
    assert getattr(s1, "digest", None) != getattr(s5, "digest", None)


def test_snapshot_hash_memo_dict_exists() -> None:
    import paxman.core.discovery as disc

    val = getattr(disc, "_snapshot_hashes", None)
    assert hasattr(disc, "_snapshot_hashes"), (
        "discovery must expose _snapshot_hashes memo dict"
    )
    assert isinstance(val, dict)


def test_discovery_freeze_reads_digest_not_sorted_tokens() -> None:
    """Ensure freeze_registry source reads matcher.digest."""
    from pathlib import Path

    repo_root = Path(__file__).resolve().parents[2]
    src = (repo_root / "paxman" / "core" / "discovery.py").read_text(encoding="utf-8")
    assert (
        "matcher.digest" in src
        or 'getattr(matcher, "digest"' in src
        or "getattr(matcher, 'digest'" in src
    ), "freeze_registry must read matcher.digest"
    freeze_section = src[
        src.find("def freeze_registry") : src.find("def is_registry_frozen")
    ]
    assert "sorted(cast(Iterable[str], tokens_set))" not in freeze_section, (
        "freeze_registry must not re-derive sorted tokens — use matcher.digest"
    )
