"""Curated canonical IANA zone-key set (rule data, tzdb 2026d snapshot).

NOT generated — edit directly. There is no snapshot snapshot + generator
script for Timezone (unlike the ISBN range message or the Currency data
set); curate by hand and keep File-Date pinned.

Source: IANA Time Zone Database, release 2026d (2026-09-11)
Reference: https://www.iana.org/time-zones
Registry files: https://raw.githubusercontent.com/eggert/tz/main/zone1970.tab
    https://raw.githubusercontent.com/eggert/tz/main/backward
File-Date: 2026d

Keys are canonical-case IANA identifiers (``America/New_York``); folding
to lower happens in the name grammar, tables stay canonical-case and the
rule restores canonical case after the fold. Every value of
``IANA_ZONE_LINKS`` (iana_zone_links.py) is a member of this set.

Curated subset: ~30 well-known keys covering every Task-4 test vector
plus the research edge corpus — NOT the full zone1970.tab universe
(~310 geographic Zones). Omitted with reason (subset contract allows):
SystemV Zones (``EST5EDT``/``PST8PDT``/``MST7MDT``/``CST6CDT`` — Zones in
``backward``, gated behind the ``include_systemv`` contract flag and owned
by the rules task); the remaining ~280 zone1970 keys; ``backzone``
(pre-1970-only, out of tzdb proper scope). Unlisted keys are MISSING at
the grammar, never INVALID.

Separation: authority-backed table serving rules only. Recognition keys
live in grammar/data; this set is the single source of truth for
identifier membership.

Extension rule: to support another canonical key, add its canonical-case
key here (and, if it is a Link target, its lowered source to
``IANA_ZONE_LINKS``);
tests/capabilities/timezone/test_data_consistency.py must stay green —
in particular every link target must resolve into this set, and no
``^[A-Z]{2,5}$`` key other than ``UTC``/``GMT`` may be added here (short
caps belong to the abbreviation family per the carve rule documented in
abbreviation_map.py).
"""

from __future__ import annotations

IANA_ZONE_IDENTIFIERS: frozenset[str] = frozenset(
    {
        # Well-known geographic keys (each zoneinfo-probed OK 2026-09-14).
        "America/New_York",
        "America/Chicago",
        "America/Denver",
        "America/Los_Angeles",
        "America/Anchorage",
        "Pacific/Honolulu",
        "America/Toronto",
        "America/Panama",  # EST Link target (backward).
        "America/Phoenix",  # MST Link target (backward).
        "Europe/London",
        "Europe/Paris",
        "Europe/Berlin",
        "Europe/Dublin",  # IST contender (theory.html).
        "Africa/Cairo",
        "Asia/Dubai",
        "Asia/Kolkata",  # Asia/Calcutta Link target; IST contender.
        "Asia/Singapore",
        "Asia/Tokyo",
        "Asia/Shanghai",  # CST contender (RFC 9636 section 5).
        "Australia/Sydney",  # Australia/ACT Link target (backward).
        "Pacific/Auckland",
        "America/Sao_Paulo",
        "Atlantic/Azores",
        "Africa/Johannesburg",
        # Fixed zones (also members of IANA_FIXED_ZONES; canonical keys).
        "Etc/UTC",
        "Etc/GMT",
        "UTC",
        "GMT",
        # Link targets outside the well-known set above.
        "Europe/Brussels",  # CET Link target (backward).
        # Abbreviation-contender zones (refusal documentation needs them
        # resolvable; each zoneinfo-probed OK 2026-09-14).
        "America/Havana",  # CST contender (RFC 9636 section 5).
        "Asia/Jerusalem",  # IST contender (theory.html).
        # Sign-trap edge vector: POSIX-inverted fixed zone, kept exactly
        # as authored (never reinterpreted); zoneinfo-probed OK 2026-09-14.
        "Etc/GMT+5",
    }
)
