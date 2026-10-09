"""MinorPlanet notation — grammar-normalized designation form."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class MinorPlanetNotation:
    """Minor-planet notation — grammar-normalized designation form.

    ``designation`` is the syntax-normalized spelled form (unpacked lanes
    uppercased, single-spaced: ``1995 XA``; surveys ``2040 P-L``; numbers
    parenthesized ``(433)``; ``A/``-prefixed ``A/2017 U1``; packed lanes
    preserved byte-for-byte, case-exact).
    ``form`` is the recognized lane (``provisional`` | ``packed`` |
    ``extended`` | ``survey`` | ``survey_packed`` | ``number`` |
    ``packed_number``) — a free str, not a Literal; the rules own lane truth.
    ``packed`` is the spelled packed form, case-EXACT, for packed lanes
    (``J95X00A``; ``a0017`` lowercase preserved) and "" for unpacked/`A/`
    lanes. Rules own decode coherence; the capability owns pack rendering.
    """

    designation: str
    form: str
    packed: str
