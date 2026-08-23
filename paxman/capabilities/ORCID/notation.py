"""ORCID notation: grammar-normalized hyphenated identifier."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ORCIDNotation:
    """ORCID normalized hyphenated form.

    ``compact`` is the 16-char separator-free uppercase string: 15 digits plus
    a check character ``0-9`` or ``X`` (value 10).
    ``hyphenated`` is the ``XXXX-XXXX-XXXX-XXXC`` presentation (three
    hyphen-minus separators, ``X`` uppercase).
    ``uri`` is ``https://orcid.org/`` + ``hyphenated`` (always https, even when
    the raw input carried ``http://``).
    ``check`` is the single check character at position 16.
    ``is_uri`` is ``"true"`` when the raw span carried an ``orcid.org`` prefix,
    else ``"false"`` (string-encoded so every field stays ``str``).

    The grammar never computes or validates the MOD 11-2 check digit; rules own
    that (grammar/rule boundary per HOW_TO_ADD_NEW_CAPABILITY.md Step 4).
    """

    compact: str
    hyphenated: str
    uri: str
    check: str
    is_uri: str
