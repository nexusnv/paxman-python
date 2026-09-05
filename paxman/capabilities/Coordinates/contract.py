from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import ClassVar

from paxman.core.contract import CapabilityContract


@dataclass(frozen=True)
class CoordinatesContract(CapabilityContract):
    """Coordinates contract — default decimal plus five offered presentations.

    Default ``decimal`` is the lat-first signed pair, quantized to 6 dp
    round-half-even. Offered formats: ``iso6709``
    (``+DD.DDDD+DDD.DDDD[/alt]/``), ``geo_uri`` (``geo:lat,lon[,alt]``),
    ``geojson_pair`` (``[lon, lat[, alt]]``, lon-first), ``dms``
    (``51°30′27″N 0°7′40″W``), ``dm`` (``51°30.445′N 0°7.6′W``).

    ``dms`` renders seconds as integers (render quantum 1″ ≈ 2.78e-4°)
    and ``dm`` renders minutes to 0.001′; both are documented
    quantizations: sub-quantum canonical digits are not recoverable from
    the rendering, re-canonicalization is a fixed point, and pre-image
    recovery drifts by at most half a render quantum — locked by
    ``tests/property/test_coordinates_quantization.py``.
    """

    DEFAULT_OUTPUT_FORMAT: ClassVar[str] = "decimal"
    OFFERED_OUTPUT_FORMATS: ClassVar[frozenset[str]] = frozenset(
        {"iso6709", "geo_uri", "geojson_pair", "dms", "dm"}
    )
    capability_name: str = field(default="coordinates", init=False)


def create_contract(  # re-exported on the capability in Task 8
    *,
    excluded_rules: Sequence[str] | None = None,
    pinned_rules: Sequence[str] | None = None,
    year: int | None = None,
    output_format: str | None = None,
    extra_grammars: Sequence[str] | None = None,
    suppress_common_words: bool = False,
) -> CoordinatesContract:
    return CoordinatesContract(
        excluded_rules=tuple(excluded_rules) if excluded_rules else (),
        pinned_rules=tuple(pinned_rules) if pinned_rules is not None else None,
        year=year,
        output_format=output_format,
        extra_grammars=tuple(extra_grammars) if extra_grammars else (),
        suppress_common_words=suppress_common_words,
    )
