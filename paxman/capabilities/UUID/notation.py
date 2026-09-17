"""UUID notation — RFC 9562 §4 carrier pre-computation.

The grammar strips braces/URN prefix, folds to lowercase, and pre-computes
every presentation so ``format_value`` selects without recomputation (ORCID
precedent). ``version`` is the informative nibble at ``compact[12]``
(``"nil"``/``"max"`` sentinels); it never gates validity (generation≠storage).
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class UUIDNotation:
    """Intermediate token for one UUID mention (carrier-free fields)."""

    compact: str  # 32-char lowercase hex, separators/prefix stripped
    hyphenated: str  # 8-4-4-4-12 lowercase canonical
    urn: str  # urn:uuid: + hyphenated (lowercase scheme)
    version: str  # hex char at compact[12], or "nil"/"max" sentinels
