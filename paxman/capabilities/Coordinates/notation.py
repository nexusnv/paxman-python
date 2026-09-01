from dataclasses import dataclass

_VALID_SHAPES = frozenset({"dd", "ddm", "dms", "iso6709", "geo_uri", "geojson"})

# Structural facts the recognition grammar records about the raw input.
# Defects are observations, not verdicts: the rules own every accept/reject
# decision and reject any notation carrying a defect it cannot accept.
_VALID_DEFECTS = frozenset(
    {
        "sign_hemisphere_conflict",
        "hemisphere_axis_mismatch",
        "dms_unit_overflow",
        "iso_digit_width",
        "iso_missing_solidus",
        "foreign_crs",
    }
)


@dataclass(frozen=True, slots=True)
class CoordinatesNotation:
    """WGS 84 coordinate - decimal pair plus input-family discriminator.

    ``latitude``/``longitude`` are sign-normalized decimal-degree strings
    (minus only, no trailing zeros, -0 folded to 0), lat-first regardless of
    input order. ``altitude`` is metres as a decimal string or None.
    ``coord_shape`` records the recognized input family so rules can apply
    the owning publication's structural law and ``format_value`` can invert
    lon-first GeoJSON input losslessly. ``defects`` records structural facts
    observed during recognition (contradictory sign/hemisphere, DMS unit
    overflow, ISO 6709 digit width, missing Annex H solidus, foreign CRS,
    hemisphere axis mismatch); the values always faithfully represent the
    input and the rule layer rejects defective notations.
    """

    latitude: str
    longitude: str
    altitude: str | None
    coord_shape: str
    compact: str
    defects: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.coord_shape not in _VALID_SHAPES:
            raise ValueError(f"invalid coord_shape: {self.coord_shape!r}")
        for defect in self.defects:
            if defect not in _VALID_DEFECTS:
                raise ValueError(f"invalid defect: {defect!r}")
