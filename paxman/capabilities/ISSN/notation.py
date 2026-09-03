"""ISSN notation: normalized digit string."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ISSNNotation:
    """ISSN normalized digit string.

    ``digits`` is the 8-character string, hyphen stripped, uppercased
    (``x`` → ``X``). The grammar never computes or validates the check digit;
    rules own that (grammar/rule boundary per HOW_TO_ADD_NEW_CAPABILITY.md §4).

    ``digits`` is syntax-normalized only; e.g. ``ISSN 0317-8471`` →
    ``"03178471"`` (label stripped, hyphen removed, ``x`` → ``X``), and
    ``ISSN03178471`` (glued) likewise. Validation, including the mod-11
    ``8→2`` check (``X=10``) per ISO 3297:2022 Section 4, is owned by
    :class:`Section4CheckDigit`. Distinct from ``ISSNContract`` output
    formats (``hyphenated``/``compact``/``urn``) which are presentation-only
    via :meth:`ISSNCapability.format_value`.
    """

    digits: str
