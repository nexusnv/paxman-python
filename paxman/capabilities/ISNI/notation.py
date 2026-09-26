"""ISNI notation: grammar-normalized spaced display identifier."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ISNINotation:
    """ISNI normalized spaced display form.

    ``compact`` is the 16-char separator-free uppercase string: 15 digits
    plus a check character ``0-9`` or ``X`` (value 10).
    ``spaced`` is the ``XXXX XXXX XXXX XXXC`` canonical display (three
    ASCII spaces, ``X`` uppercase) per ISO 27729 §4 human-readable rule.
    ``uri`` is ``https://isni.org/isni/`` + ``compact`` (always https,
    even when the raw input carried ``http://`` or ``www.``).
    ``check`` is the single check character at position 16.
    ``is_uri`` is ``"true"`` when the raw span carried an ``isni.org``
    prefix or ``urn:isni:`` carrier, else ``"false"`` (string-encoded so
    every field stays ``str``).
    The grammar never computes or validates the MOD 11-2 check digit;
    rules own that (grammar/rule boundary per HOW_TO_ADD_NEW_CAPABILITY.md
    Step 4).
    """

    compact: str
    spaced: str
    uri: str
    check: str
    is_uri: str
