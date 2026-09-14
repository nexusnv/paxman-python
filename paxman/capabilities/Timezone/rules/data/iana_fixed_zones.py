"""IANA etcetera fixed zones + bare UTC/GMT (rule data, tzdb 2026d snapshot).

NOT generated — edit directly. There is no snapshot + generator script
for Timezone; curate by hand and keep File-Date pinned.

Source: IANA Time Zone Database, release 2026d (2026-09-11)
Reference: https://www.iana.org/time-zones
Registry files: https://raw.githubusercontent.com/eggert/tz/main/backward
    https://data.iana.org/time-zones/theory.html
File-Date: 2026d

``UTC`` is ``Link Etc/UTC UTC`` in ``backward`` and ``GMT`` resolves via
the ``etcetera`` zones (the Vanguard ``Link GMT Etc/GMT`` lines are
commented out in ``backward`` — GMT is zone-defined, not a Link); both
are therefore fixed zones, NOT abbreviations, and are exempt from the
carve rule (see abbreviation_map.py). Both zoneinfo-probed OK 2026-09-14
(``ZoneInfo("UTC")``, ``ZoneInfo("GMT")``); ``Etc/UTC``/``Etc/GMT``
likewise probed OK.

Separation: authority-backed table serving rules only. Recognition keys
live in grammar/data.

Extension rule: to support another fixed zone (e.g. a further ``Etc/*``
key), add its canonical-case key here AND to ``IANA_ZONE_IDENTIFIERS``;
tests/capabilities/timezone/test_data_consistency.py must stay green.
"""

from __future__ import annotations

IANA_FIXED_ZONES: frozenset[str] = frozenset(
    {
        "Etc/UTC",
        "Etc/GMT",
        "UTC",
        "GMT",
    }
)
