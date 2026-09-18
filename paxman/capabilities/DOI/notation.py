"""DOI notation — prefix/suffix decomposition of a DOI name.

Per ISO 26324:2025 via the DOI Handbook Ch.3 (DOI Namespace): a DOI name is
a prefix and a suffix separated by U+002F SOLIDUS. The prefix carries the
``10.`` directory indicator plus registrant code; the suffix is the
registrant-chosen opaque string. ``canonical`` is the ASCII-folded
``prefix/suffix`` default-format value (Handbook 'Case Insensitivity':
equivalence is Basic-Latin-only with no normalization).
"""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class DOINotation:
    """DOI prefix/suffix split; canonical is the default-format value."""

    prefix: str  # e.g. "10.1038" — 10.<registrant>, ASCII-folded
    suffix: str  # e.g. "nature12345" — ASCII-folded, percent-escapes literal
    canonical: str  # prefix + "/" + suffix, the default-format value
