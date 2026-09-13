"""Hand-maintained script display-name recognition keys (grammar data).

NOT generated — edit directly. (This module carries no generator; the
GENERATED-locked english_names.py / english_language_map.py precedent
does not apply here.)

Source: IANA Language Subtag Registry
Reference: https://www.iana.org/assignments/language-subtag-registry/language-subtag-registry
File-Date: 2026-08-08
Subtags covered: Hant ("Han (Traditional variant)"), Hans ("Han (Simplified variant)").
Keys are normalize_name() output (lower, accent-stripped, space-collapsed).

Completeness: curated subset (acceptance-required minimum for
compositional descriptions such as "Chinese in traditional script").
Script display names outside this subset are MISSING (grammar emits no
match), not INVALID — no false negative under the current completeness
contract. Broader script coverage is follow-up work on #148.

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
    }
)
