"""Curated abbreviation carve + refusal sets (rule data, tzdb 2026d snapshot).

NOT generated — edit directly. There is no snapshot + generator script
for Timezone; curate by hand and keep File-Date pinned.

Source: IANA Time Zone Database, release 2026d (2026-09-11)
Reference: https://www.iana.org/time-zones
Registry file: https://raw.githubusercontent.com/eggert/tz/main/backward
    (carve entries verified as Link lines in-file 2026-09-14)
Ambiguity evidence: https://data.iana.org/time-zones/theory.html
    (IST India/Ireland/Israel), RFC 9636 section 5 (CST x3)
File-Date: 2026d

Keys are lowered abbreviation tokens (the abbreviation grammar is
UPPER-exact; the rule folds to lower before lookup). Both sets refuse:
membership means the abbreviation rule returns False (INVALID), never a
silent pick.

``CARVED_LINKS`` — short-caps ``backward`` Links carved out of the name
lexicon into the abbreviation family (identifier equivalence is not
lexical abbreviation equivalence):
``est`` -> America/Panama, ``mst`` -> America/Phoenix,
``hst`` -> Pacific/Honolulu, ``cet`` -> Europe/Brussels.
Keep in sync with the short-caps entries of ``IANA_ZONE_LINKS``
(iana_zone_links.py), which declares the Link targets this rule refuses
to resolve. ``UTC``/``GMT`` are zone-defined fixed zones, never carve
members (see iana_fixed_zones.py).

``REFUSAL_SET`` — ambiguous abbreviations with NO ``backward`` Link,
refused because no single zone can be chosen honestly. Only the
evidence-verified ambiguous tokens are listed:
``ist`` (Asia/Kolkata, Europe/Dublin, Asia/Jerusalem per theory.html),
``cst`` (America/Chicago, Asia/Shanghai, America/Havana per RFC 9636
section 5), ``pst`` (America/Los_Angeles plus historical Philippine use
per theory.html).

Omitted with reason (subset contract allows; unlisted = MISSING at the
grammar, never INVALID): ``jst``/``msk`` (no ``backward`` Link lines —
unverified for v1) and ``wet``/``eet`` (``Link Europe/Lisbon WET`` and
``Link Europe/Athens EET`` DO exist in ``backward``, but v1 scopes the
carve set to the four research-attested tokens above). To admit any of
these, verify its ``backward``/theory.html status, add it to
``CARVED_LINKS`` (with its ``IANA_ZONE_LINKS`` entry) or ``REFUSAL_SET``
accordingly, and document its contenders here.

Separation: authority-backed table serving rules only. Recognition keys
live in grammar/data.

Extension rule: carve and refusal sets must stay disjoint, and no member
of either set may appear in ``IANA_ZONE_IDENTIFIERS`` except via the
UTC/GMT fixed-zone exemption;
tests/capabilities/timezone/test_data_consistency.py must stay green.
"""

from __future__ import annotations

# Ambiguous abbreviations with no backward Link — refused, never resolved.
REFUSAL_SET: frozenset[str] = frozenset(
    {
        "ist",
        "cst",
        "pst",
    }
)

# Short-caps backward Links — declared in IANA_ZONE_LINKS but refused
# here; the abbreviation rule owns these tokens, the name rule never sees
# them.
CARVED_LINKS: frozenset[str] = frozenset(
    {
        "est",
        "mst",
        "hst",
        "cet",
    }
)
