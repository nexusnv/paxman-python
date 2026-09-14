"""ISO 8601-1:2019 UTC offset representations (standalone values).

Offset shape plus range: ``Z`` / reduced ``+-HH`` / basic ``+-HHMM`` /
extended ``+-HH:MM``, each with an optional ``UTC``/``GMT`` human-notation
prefix. Minutes are bounded by ``MM < 60`` and the signed total by
``-12:00..+14:00`` (Baker Island .. Kiritimati) — a total-minutes bound,
not independent HH/MM caps, so ``+14:30`` (observed nowhere on Earth) is
refused while ``+14:00`` stays valid. The RFC 3339 unknown-offset
``-00:00`` states ignorance of the offset and is refused. Valid mentions
normalize to canonical extended ``+HH:MM``.
"""

from __future__ import annotations

from typing import ClassVar

from paxman.capabilities.UtcOffset.notation import UtcOffsetNotation
from paxman.core.contract import Contract
from paxman.core.domain import Provenance, Rule, RuleStrategy

PUBLICATION = Provenance(
    authority="ISO",
    specification_name="ISO 8601-1",
    kind="specification",
    reference_url="https://www.iso.org/standard/70907.html",
    version="2019",
    lifecycle="active",
    publication_year=2019,
)

_DIGITS = frozenset("0123456789")
_MAX_MINUTES = 59
# Real-world UTC offset range in signed total minutes: -12:00 (Baker
# Island, UTC-12:00) through +14:00 (Kiritimati, UTC+14:00). The bound is
# on the total — not independent HH/MM caps — so +14:30 (observed nowhere
# on Earth) is refused while +14:00 stays valid.
_MIN_TOTAL_MINUTES = -720
_MAX_TOTAL_MINUTES = 840


def _is_ascii_digits(text: str) -> bool:
    """Whether ``text`` is a non-empty run of ASCII digits."""
    return bool(text) and all(char in _DIGITS for char in text)


def _parse_offset(compact: str) -> tuple[str, int, int] | None:
    """Parse offset text into ``(sign, hours, minutes)``, else None.

    Accepts ``Z``/``z``, ``+-H``/``+-HH``/``+-HHMM``/``+-H:MM``/``+-HH:MM``
    with an optional case-insensitive ``UTC``/``GMT`` prefix. Total
    function: malformed shapes, out-of-range fields, and negative zero
    (unknown-offset in any accepted form) all yield None, never raise.
    """
    if not isinstance(compact, str):
        return None
    text = compact.strip()
    if not text:
        return None
    if len(text) == 1 and text in ("Z", "z"):
        return ("+", 0, 0)
    body = text
    if body[:3].upper() in ("UTC", "GMT"):
        body = body[3:]
    if len(body) < 2 or body[0] not in ("+", "-"):
        return None
    sign = body[0]
    rest = body[1:]
    if not rest:
        return None
    hours = 0
    minutes = 0
    if ":" in rest:
        parts = rest.split(":")
        if len(parts) != 2:
            return None
        hour_part, minute_part = parts
        if not _is_ascii_digits(hour_part) or not _is_ascii_digits(minute_part):
            return None
        if not 1 <= len(hour_part) <= 2 or len(minute_part) != 2:
            return None
        hours = int(hour_part)
        minutes = int(minute_part)
    else:
        if not _is_ascii_digits(rest) or len(rest) not in (1, 2, 4):
            return None
        if len(rest) <= 2:
            hours = int(rest)
        else:
            hours = int(rest[:2])
            minutes = int(rest[2:])
    if minutes > _MAX_MINUTES:
        return None
    total_minutes = hours * 60 + minutes
    signed_total = total_minutes if sign == "+" else -total_minutes
    if not _MIN_TOTAL_MINUTES <= signed_total <= _MAX_TOTAL_MINUTES:
        return None
    if sign == "-" and hours == 0 and minutes == 0:
        return None
    return (sign, hours, minutes)


class SectionOffsetStructure(Rule[UtcOffsetNotation]):
    """ISO 8601 offset structure and range, normalized to ``+HH:MM``."""

    name = "Section offset-structure"
    strategy = RuleStrategy.PARSER
    provenance = PUBLICATION
    citation = (
        "ISO 8601-1:2019 Section 3 (offset representations); "
        "RFC 3339 Section 5.6 (time-numoffset +-HH:MM, Z)"
    )
    target_semantics: ClassVar[frozenset[str]] = frozenset({"utc_offset"})
    requires_features: ClassVar[frozenset[str]] = frozenset()

    def matches(self, notation: UtcOffsetNotation, contract: Contract) -> bool:
        return _parse_offset(notation.compact) is not None

    def normalize(self, notation: UtcOffsetNotation, contract: Contract) -> str:
        parsed = _parse_offset(notation.compact)
        if parsed is None:
            # defensive: never raise; unreachable after matches()
            compact = notation.compact
            if not isinstance(compact, str):
                return "" if compact is None else str(compact)
            return compact
        sign, hours, minutes = parsed
        return f"{sign}{hours:02d}:{minutes:02d}"
