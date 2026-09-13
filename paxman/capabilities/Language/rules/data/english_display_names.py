"""Hand-maintained canonical-code → English display-name companion (rule data).

NOT generated — edit directly. (This module carries no generator; the
GENERATED-locked english_language_map.py precedent does not apply here —
that file must not be touched, so true display forms live in this
separate companion table.)

Source: IANA Language Subtag Registry
Reference: https://www.iana.org/assignments/language-subtag-registry/language-subtag-registry
File-Date: 2026-08-08

Keys are lower canonical language codes (alpha-2 when available, else
alpha-3 Term — the same code space ``format_value(..., "name")`` resolves
its reverse lookup to). Values are the true IANA Description display
forms, preserving diacritics that ``language_snapshot.json``
normalization strips (``"norwegian bokmal"`` → ``"Norwegian Bokmål"``).

Completeness: curated subset (1 entry — the reported B6 vector). Other
diacritic-losers cannot be enumerated without an external source, so the
table starts at Bokmål rather than guessing. Codes without an entry fall
back to ``title()`` of the normalized English key in
``LanguageCapability.format_value`` — the fallback stays for unlisted codes.

Separation: authority-backed table serving the presentation seam
(``format_value``) only. Recognition keys live in grammar/data; the
canonical mapping in english_language_map.py remains the single source
of truth for name meaning.

Extension rule: to support another display form, add its canonical code
and IANA Description here;
tests/capabilities/language/test_capability.py::TestLanguageFormatValue::test_name_orthography
must stay green.
"""

from __future__ import annotations

ENGLISH_DISPLAY_NAMES: dict[str, str] = {
    "nb": "Norwegian Bokmål",
}
