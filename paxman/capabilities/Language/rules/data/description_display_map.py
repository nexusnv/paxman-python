"""Hand-maintained display-name to subtag authority mapping (rule data).

NOT generated — edit directly. (This module carries no generator; the
GENERATED-locked english_language_map.py precedent does not apply here —
that file must not be touched, so compositional display mappings live in
this separate file.)

Source: IANA Language Subtag Registry
Reference: https://www.iana.org/assignments/language-subtag-registry/language-subtag-registry
File-Date: 2026-08-08

Keys are normalize_name() output (lower, accent-stripped, space-collapsed);
each key is a member of SCRIPT_DISPLAY_KEYS (grammar/data/script_names.py)
or REGION_DISPLAY_KEYS (grammar/data/region_names.py). Values are
canonical-case subtags matching LanguageNotation fields (script Title,
region Upper): "traditional" -> Hant, "simplified" -> Hans,
"singapore" -> SG.

Separation: authority-backed table serving rules only. Recognition keys
live in grammar/data; this mapping is the single source of truth for
display-name meaning.

Extension rule: to support another display name, add its key to the
grammar/data set AND its entry here;
tests/capabilities/language/test_data_consistency.py must stay green.
"""

from __future__ import annotations

DESCRIPTION_DISPLAY_MAP: dict[str, str] = {
    "traditional": "Hant",
    "simplified": "Hans",
    "singapore": "SG",
    # Wave 2 scripts (#148) — one contiguous block (Task 3 appends region
    # entries after this block). Each value IANA-Registry-verified
    # (File-Date 2026-08-08) and pre-shipped in iana_script_subtags.py.
    "latin": "Latn",
    "cyrillic": "Cyrl",
    "arabic": "Arab",
    "devanagari": "Deva",
    "greek": "Grek",
    "hebrew": "Hebr",
    "armenian": "Armn",
    # Wave 2 regions (#148) — one contiguous block after the script block.
    # Each value IANA-Registry-verified (File-Date 2026-08-08) and
    # pre-shipped in iana_region_subtags.py. Multi-token regions
    # (e.g. united states -> US) stay out by design.
    "germany": "DE",
    "france": "FR",
    "japan": "JP",
    "china": "CN",
    "india": "IN",
    "brazil": "BR",
    "canada": "CA",
    "australia": "AU",
}
