from dataclasses import dataclass

_VALID_SHAPES = frozenset({"dd", "ddm", "dms", "iso6709", "geo_uri", "geojson"})


@dataclass(frozen=True, slots=True)
class CoordinatesNotation:
    """WGS 84 coordinate - decimal pair plus input-family discriminator.

    ``latitude``/``longitude`` are sign-normalized decimal-degree strings
    (minus only, no trailing zeros, -0 folded to 0), lat-first regardless of
    input order. ``altitude`` is metres as a decimal string or None.
    ``coord_shape`` records the recognized input family so rules can apply
    the owning publication's structural law and ``format_value`` can invert
    lon-first GeoJSON input losslessly.
    """

    latitude: str
    longitude: str
    altitude: str | None
    coord_shape: str
    compact: str

    def __post_init__(self) -> None:
        if self.coord_shape not in _VALID_SHAPES:
            raise ValueError(f"invalid coord_shape: {self.coord_shape!r}")
