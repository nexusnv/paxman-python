"""Curated IANA Link -> canonical-key map (rule data, tzdb 2026d snapshot).

NOT generated — edit directly. There is no snapshot + generator script
for Timezone; curate by hand and keep File-Date pinned.

Source: IANA Time Zone Database, release 2026d (2026-09-11)
Reference: https://www.iana.org/time-zones
Registry file: https://raw.githubusercontent.com/eggert/tz/main/backward
    (each line below verified against the live ``backward`` file 2026-09-14)
File-Date: 2026d

Keys are lowered Link names (the name grammar folds to lower before
lookup); values are canonical-case keys, each a member of
``IANA_ZONE_IDENTIFIERS`` (iana_zone_identifiers.py).

Carve rule: the short-caps entries (``est``/``mst``/``hst``/``cet``) are
present here because ``backward`` declares the Links, BUT they are
consumed only by the abbreviation rule, never by the name rule — the
name lexicon excludes short-caps Links into the abbreviation family,
whose rule refuses them (identifier equivalence is not lexical
abbreviation equivalence). The literal-Link seeker writes the canonical
key. ``CARVED_LINKS`` in abbreviation_map.py is the enforcement list;
keep the two in sync.

``australia/act`` note: ``backward`` reads
``Link Australia/Sydney Australia/ACT  #= Australia/Canberra`` — the
file links to ``Australia/Sydney`` (a link-to-link workaround comment
names ``Australia/Canberra`` as the would-be target), so the vendored
target is ``Australia/Sydney`` exactly as declared.

Separation: authority-backed table serving rules only. Recognition keys
live in grammar/data; this map is the single source of truth for Link
resolution.

Extension rule: to support another Link, add its lowered source here
with its canonical-case target AND ensure the target is in
``IANA_ZONE_IDENTIFIERS`` (add it there first if missing); short-caps
additions also require a ``CARVED_LINKS`` entry in abbreviation_map.py;
tests/capabilities/timezone/test_data_consistency.py must stay green.
"""

from __future__ import annotations

IANA_ZONE_LINKS: dict[str, str] = {
    # Legacy path Links (Link TARGET LINK-NAME, verified in-file).
    "us/eastern": "America/New_York",
    "asia/calcutta": "Asia/Kolkata",
    "australia/act": "Australia/Sydney",
    # Short-caps Links — declared here, consumed ONLY by the abbreviation
    # rule per the carve rule above (name rule must never resolve these).
    "cet": "Europe/Brussels",
    "est": "America/Panama",
    "mst": "America/Phoenix",
    "hst": "Pacific/Honolulu",
}
