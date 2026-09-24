"""Shared IDNA processing for the Domain capability (UTS #46 map step).

Grammar-side mapping plus rule-side encoding helpers, kept in one
capability-root module so grammars and rules share a single implementation
without importing each other (the purity scan bans grammar<->rules
imports, not capability-root imports). Table-only mapping: the shipped
15.1.0 table carries the case mapping itself (``0041;mapped;0061``), so no
``str.casefold`` is applied — mapping, then NFC, then split.
"""

from __future__ import annotations

import unicodedata
from bisect import bisect_right
from collections.abc import Sequence

from paxman.capabilities.Domain.grammar.data.idna_mapping import (
    MAPPING,
    STATUSES,
)


def _build_intervals() -> tuple[tuple[int, int, str], ...]:
    """Sorted (start, end, status) intervals from the range-keyed table."""
    out: list[tuple[int, int, str]] = []
    for key, status in STATUSES.items():
        if ".." in key:
            start, _, end = key.partition("..")
            out.append((int(start, 16), int(end, 16), status))
        else:
            cp = int(key, 16)
            out.append((cp, cp, status))
    return tuple(sorted(out))


_STATUS_INTERVALS = _build_intervals()
_STATUS_STARTS = tuple(start for start, _, _ in _STATUS_INTERVALS)


def status_of(codepoint: int) -> str:
    """UTS #46 status of one code point; unlisted code points are valid."""
    idx = bisect_right(_STATUS_STARTS, codepoint) - 1
    if idx >= 0:
        start, end, status = _STATUS_INTERVALS[idx]
        if start <= codepoint <= end:
            return status
    return "valid"


def map_domain(text: str) -> tuple[str, ...]:
    """Map raw input to the mapped label tuple (non-transitional map step).

    Per character: apply MAPPING for ``mapped`` rows (targets may be
    space-separated multi-codepoint sequences — expand each), drop
    ``ignored`` code points, keep ``deviation``/``disallowed`` verbatim
    (deviation stays under non-transitional processing; disallowed is
    rejected later by the statuses rule). Then NFC, split on ``.``,
    strip ONE trailing empty label.
    """
    mapped_chars: list[str] = []
    for char in text:
        codepoint = ord(char)
        target = MAPPING.get(codepoint)
        if target is not None:
            mapped_chars.append(
                "".join(chr(int(part, 16)) for part in target.split(" "))
            )
        elif status_of(codepoint) == "ignored":
            continue
        else:
            mapped_chars.append(char)
    normalized = unicodedata.normalize("NFC", "".join(mapped_chars))
    labels = normalized.split(".")
    if labels and labels[-1] == "":
        labels = labels[:-1]
    return tuple(labels)


def ace_encode(label: str) -> str:
    """Encode one mapped label to its A-label form (ASCII passthrough)."""
    if label.isascii():
        return label
    return "xn--" + label.encode("punycode").decode("ascii")


def ace_decode_ok(label: str) -> bool:
    """Verify an ``xn--`` label is well-formed ACE (decode/re-encode round trip).

    Non-ACE labels pass vacuously. Requires a non-empty ASCII payload, a
    non-empty decode, and an exact ``"xn--" + reencode == label`` round trip
    (guards the empty-decode bypass).
    """
    if not label.startswith("xn--"):
        return True
    payload = label[4:]
    if not payload or not payload.isascii():
        return False
    try:
        decoded = payload.encode("ascii").decode("punycode")
    except UnicodeError:
        return False
    if not decoded:
        return False
    return "xn--" + decoded.encode("punycode").decode("ascii") == label


def ace_decode(label: str) -> str:
    """Decode an ``xn--`` label to its U-label form; failure returns it unchanged."""
    if not label.startswith("xn--"):
        return label
    payload = label[4:]
    if not payload or not payload.isascii():
        return label
    try:
        decoded = payload.encode("ascii").decode("punycode")
    except UnicodeError:
        return label
    if not decoded:
        return label
    return decoded


def finalize(labels: Sequence[str]) -> str:
    """Encode mapped labels to the canonical A-label dotted name."""
    return ".".join(ace_encode(label) for label in labels)
