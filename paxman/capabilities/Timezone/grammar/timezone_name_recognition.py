"""Timezone name recognition grammar — IANA identifier keys and Links.

Lexicon over lowered identifier keys on the ``casefolded`` view; the
rule restores canonical case after the fold (folding is safe by
namespace construction — tzdb POSIX component rules forbid
case-variant collisions). Edges exclude word chars AND ``/`` (a
``BoundarySpec`` composition — the kernel already expresses the slash
guard, so no capability-local guard is needed): no mid-path extraction
from zoneinfo paths, no glued runs. Short-caps backward Links
(``EST``/``CET``/…) are carved out into the abbreviation family —
see ``timezone_abbreviation_recognition.py``.

Recognition keys below mirror the vendored tzdb 2026d snapshot
(``iana_zone_identifiers``, ``iana_zone_links``, ``iana_fixed_zones``,
minus the carved Links); keys only, never a mapping — the grammar
tests assert parity with those tables so the two cannot drift, and
this module imports nothing from ``rules`` (grammar/rule separation
is structural).
"""

from __future__ import annotations

from paxman.capabilities.Timezone.notation import TimezoneNotation
from paxman.core.grammar import (
    AnchorSet,
    BoundarySpec,
    PipelineGrammar,
    StandardPre,
)
from paxman.core.grammar.matchers.lexicon import LexiconMatcher
from paxman.core.grammar.scan_context import ScanContext

# Lowered recognition keys (tzdb 2026d snapshot, curated subset).
# Groups below record which table each key comes from; Link targets
# live in rules/data and are never repeated here (keys only).
NAME_TOKENS: frozenset[str] = frozenset(
    {
        # Geographic identifier keys (lowered).
        "africa/cairo",
        "africa/johannesburg",
        "america/anchorage",
        "america/chicago",
        "america/denver",
        "america/havana",
        "america/los_angeles",
        "america/new_york",
        "america/panama",
        "america/phoenix",
        "america/sao_paulo",
        "america/toronto",
        "asia/dubai",
        "asia/jerusalem",
        "asia/kolkata",
        "asia/shanghai",
        "asia/singapore",
        "asia/tokyo",
        "atlantic/azores",
        "australia/sydney",
        "europe/berlin",
        "europe/brussels",
        "europe/dublin",
        "europe/london",
        "europe/paris",
        "pacific/auckland",
        "pacific/honolulu",
        # Legacy Link keys (lowered; short-caps Links carved out).
        "asia/calcutta",
        "australia/act",
        "canada/eastern",
        "us/eastern",
        "us/pacific",
        # Fixed zones (lowered).
        "etc/gmt",
        "etc/gmt+5",
        "etc/gmt-8",
        "etc/utc",
        "gmt",
        "utc",
        # POSIX SystemV Zones (lowered): claimed here for shape; the rule
        # gates them behind ``include_systemv`` (default INVALID, +flag
        # SUCCESS). Owned by SectionSystemVZones, excluded by the
        # always-active sections.
        "est5edt",
        "cst6cdt",
        "mst7mdt",
        "pst8pdt",
    }
)

# Slash-aware edges: a claim must not start/end glued to a word char
# or a slash (mac_midrun precedent, expressed as BoundarySpec). The
# multi-char right fragment additionally voids offset continuations
# ("Etc/GMT+5X" must not fall back to the "Etc/GMT" prefix — the group
# declines frozenset lowering, so it checks the full remainder).
_NAME_BOUNDARY = BoundarySpec(
    left=(r"[\w/]",), right=(r"[\w/]", r"(?:[+-][0-9])"), mode="zero_width"
)


def _emit(span: tuple[int, int], ctx: ScanContext) -> TimezoneNotation:
    """Emit a name-family notation preserving the as-written mention."""
    s, e = span
    raw = ctx.text[s:e]
    return TimezoneNotation(key=raw, family="name", compact=raw)


_NAME_MATCHER = LexiconMatcher(
    tokens=NAME_TOKENS,
    boundary=_NAME_BOUNDARY,
    view="casefolded",
    anchors=AnchorSet(),
    emit=_emit,
    representation="trie",
)


class TimezoneNameGrammar(PipelineGrammar[TimezoneNotation]):
    """Recognizes IANA zone identifiers and legacy Links, case-insensitive.

    Emits the as-written mention with family ``"name"``; rules own
    membership, Link resolution, and canonical-case restoration.

    Examples: "America/New_York" → key="America/New_York"
              "US/Eastern" → key="US/Eastern"
              "america/new_york" → key="america/new_york"
    Non-examples: "EST" → [] (abbreviation family)
                  "XUS/Eastern" → [] (glued run)
                  "/usr/share/zoneinfo/America/New_York" → [] (path context)
    """

    name = "timezone_name_recognition"
    semantics = "timezone_name"
    single_value = True

    pre = StandardPre[TimezoneNotation](empty_guard=True)
    matchers = (_NAME_MATCHER,)
