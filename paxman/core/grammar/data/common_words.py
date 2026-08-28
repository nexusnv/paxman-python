"""Common-word suppression table — provenance-neutral by construction.

Derived intersection (lowercased, reviewable):
  Google 1000 most-common English words ∩ (ISO3166 α2/α3 + ISO4217 + ISO639)

Source:
  Google 1000: https://github.com/first20hours/google-10000-english
  File: google-10000-english.txt (first 1000 lines, ranks 1..1000)
  Fetched: 2026-08-26; lowercased for intersection.

ISO sets (shipped, frozen):
  ISO 3166-1 α2: .../Country/rules/data/iso_3166_ed2024.py
    ALPHA2_CODES (250)
  ISO 3166-1 α3: same module ALPHA3_TO_ALPHA2 keys (250)
  ISO 4217: .../Currency/rules/data/iso4217_list_one.py
    CURRENCY_CODES (178)
  ISO 639-1: .../Language/rules/data/iso_639_1.py
    ISO6391_CODES (184)
  ISO 639-2 T/B: .../Language/rules/data/iso_639_2.py (420+21)
  ISO 639-3: .../Language/rules/data/iso_639_3.py
    ISO6393_CODES (995)

Derivation (reproducible, captured 2026-08-26):
  google1000 = {w.lower() for w in first 1000 lines of google-10000-english.txt}
  short = {c.lower() for c in ALPHA2} ∪ {c.lower() for c in ALPHA3}
          ∪ {c.lower() for c in CURRENCY_CODES}
          ∪ ISO6391 ∪ ISO6392_T ∪ ISO6392_B ∪ {c.lower() for c in ISO6393}
  COMMON_WORDS = google1000 ∩ short  (lowercased)

Invariants:
  - Suppression removes a recognition; it never canonicalizes (provenance-neutral).
    A suppressed span is simply not emitted — no validation, no provenance.
  - Default off: CapabilityContract.suppress_common_words=False preserves byte-identical
    behavior for every existing caller.
  - USD must never be suppressed (currency code collision with word "usd" is not in
    Google 1000, but explicitly guarded).
  - Size frozen: assert len == 67; drift requires intentional edit and review.
  - Requires word-boundary via BoundarySpec already (engine_loop insertion only for
    matchers with word boundaries; see ADR-0009 §16).
"""

from __future__ import annotations

COMMON_WORDS: frozenset[str] = frozenset(
    {
        "act",
        "add",
        "age",
        "ago",
        "air",
        "al",
        "all",
        "am",
        "an",
        "and",
        "any",
        "apr",
        "are",
        "as",
        "ask",
        "at",
        "aug",
        "be",
        "by",
        "ca",
        "can",
        "car",
        "cd",
        "co",
        "de",
        "do",
        "en",
        "et",
        "gay",
        "got",
        "he",
        "her",
        "him",
        "id",
        "ii",
        "in",
        "is",
        "it",
        "la",
        "man",
        "mar",
        "may",
        "me",
        "men",
        "my",
        "new",
        "no",
        "non",
        "or",
        "per",
        "pm",
        "pro",
        "re",
        "run",
        "san",
        "so",
        "st",
        "sun",
        "to",
        "top",
        "try",
        "tv",
        "uk",
        "us",
        "usa",
        "war",
        "was",
    }
)

assert len(COMMON_WORDS) == 67
assert "USD" not in COMMON_WORDS
assert "usd" not in COMMON_WORDS
