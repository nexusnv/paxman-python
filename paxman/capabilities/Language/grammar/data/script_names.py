"""Hand-maintained script display-name recognition keys (grammar data).

NOT generated — edit directly. (This module carries no generator; the
GENERATED-locked english_names.py / english_language_map.py precedent
does not apply here.)

Source: IANA Language Subtag Registry
Reference: https://www.iana.org/assignments/language-subtag-registry/language-subtag-registry
File-Date: 2026-08-08
Subtags covered: Hant ("Han (Traditional variant)"), Hans ("Han (Simplified variant)"),
  Latn ("Latin"), Cyrl ("Cyrillic"), Arab ("Arabic"), Deva ("Devanagari"),
  Grek ("Greek"), Hebr ("Hebrew"), Armn ("Armenian").
Keys are normalize_name() output (lower, accent-stripped, space-collapsed).

Completeness: curated subset (acceptance-required minimum plus Wave-2
major scripts for compositional descriptions such as
"German in Latin script"). Wave 2 (#148): latin, cyrillic, arabic,
devanagari, greek, hebrew, plus armenian (script display name identical
to a language name — positional slots disambiguate, pinned by an
explicit test). Script display names outside this subset are MISSING
(grammar emits no match), not INVALID — no false negative under the
current completeness contract. Broader script coverage (e.g. thai,
whose subtag is absent from the shipped IANA script set) stays on #148.

Extension rule: to support another script display name, add its
normalize_name() key here AND its canonical-subtag entry in
paxman/capabilities/Language/rules/data/description_display_map.py;
tests/capabilities/language/test_data_consistency.py must stay green.

Separation: grammar data — keys only, no subtag mapping.
"""

from __future__ import annotations

SCRIPT_DISPLAY_KEYS: frozenset[str] = frozenset(
    {
        "traditional",
        "simplified",
        # Wave 2 (#148) — one contiguous block; Task 3 appends region
        # entries to description_display_map.py, not here.
        "latin",
        "cyrillic",
        "arabic",
        "devanagari",
        "greek",
        "hebrew",
        "armenian",
    }
)
