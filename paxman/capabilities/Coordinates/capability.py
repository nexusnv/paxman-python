"""Coordinates capability — WGS 84 point, six output formats."""

from __future__ import annotations

from collections.abc import Sequence
from decimal import ROUND_HALF_EVEN, Decimal, InvalidOperation

from paxman.capabilities.Coordinates.contract import CoordinatesContract
from paxman.capabilities.Coordinates.grammar.coordinates_recognition import (
    CoordinatesRecognitionGrammar,
)
from paxman.capabilities.Coordinates.notation import CoordinatesNotation
from paxman.capabilities.Coordinates.rules.iso_6709_ed2022 import (
    Section6CoordinateStructure,
    SectionAnnexHStringExpression,
)
from paxman.capabilities.Coordinates.rules.rfc_5870_ed2010 import (
    Section33GeoUriValidity,
)
from paxman.capabilities.Coordinates.rules.rfc_7946_ed2016 import Section311Position
from paxman.core.capability import Capability
from paxman.core.domain import Grammar, Rule


def _quantized_str(value: Decimal) -> str:
    """Quantize to 6dp half-even, strip trailing zeros, fold -0."""
    try:
        q = value.quantize(Decimal("0.000001"), rounding=ROUND_HALF_EVEN)
    except InvalidOperation:
        return format(value, "f")
    if q == 0:
        return "0"
    qn = q.normalize()
    if qn == 0:
        return "0"
    return format(qn, "f")


def _decimal_to_dms_parts(decimal_str: str, is_lat: bool) -> tuple[int, int, int, str]:
    """Convert decimal-degree string to (deg, min, sec, hemi)."""
    dec = Decimal(decimal_str)
    hemi = ("N" if dec >= 0 else "S") if is_lat else ("E" if dec >= 0 else "W")
    abs_dec = abs(dec)
    deg = int(abs_dec)
    rem = abs_dec - Decimal(deg)
    minutes_full = rem * Decimal(60)
    minute = int(minutes_full)
    sec_full = (minutes_full - Decimal(minute)) * Decimal(60)
    sec_dec = sec_full.quantize(Decimal("1"), rounding=ROUND_HALF_EVEN)
    sec = int(sec_dec)
    if sec == 60:
        sec = 0
        minute += 1
    if minute == 60:
        minute = 0
        deg += 1
    return deg, minute, sec, hemi


def _decimal_to_dm_parts(decimal_str: str, is_lat: bool) -> tuple[int, Decimal, str]:
    """Convert decimal-degree string to (deg, decimal_minutes, hemi)."""
    dec = Decimal(decimal_str)
    hemi = ("N" if dec >= 0 else "S") if is_lat else ("E" if dec >= 0 else "W")
    abs_dec = abs(dec)
    deg = int(abs_dec)
    rem = abs_dec - Decimal(deg)
    minutes = rem * Decimal(60)
    minutes_q = minutes.quantize(Decimal("0.001"), rounding=ROUND_HALF_EVEN)
    if minutes_q == Decimal(60):
        minutes_q = Decimal("0")
        deg += 1
        if is_lat and deg > 90:
            deg = 90
            minutes_q = Decimal("0")
        if not is_lat and deg > 180:
            deg = 180
            minutes_q = Decimal("0")
    return deg, minutes_q, hemi


def _format_iso(lat_str: str, lon_str: str, alt_str: str | None) -> str:
    """ISO 6709 string expression: +DD.DDDD+DDD.DDDD/ with altitude."""
    lat_dec = Decimal(lat_str)
    lon_dec = Decimal(lon_str)
    lat_sign = "+" if lat_dec >= 0 else "-"
    lon_sign = "+" if lon_dec >= 0 else "-"
    lat_abs_str = lat_str.lstrip("-")
    lon_abs_str = lon_str.lstrip("-")
    if "." in lat_abs_str:
        lat_int, lat_frac = lat_abs_str.split(".", 1)
        lat_frac = "." + lat_frac
    else:
        lat_int, lat_frac = lat_abs_str, ""
    if "." in lon_abs_str:
        lon_int, lon_frac = lon_abs_str.split(".", 1)
        lon_frac = "." + lon_frac
    else:
        lon_int, lon_frac = lon_abs_str, ""
    lat_int_padded = lat_int.zfill(2)
    lon_int_padded = lon_int.zfill(3)
    lat_iso = f"{lat_sign}{lat_int_padded}{lat_frac}"
    lon_iso = f"{lon_sign}{lon_int_padded}{lon_frac}"
    alt_part = ""
    if alt_str is not None:
        alt_dec = Decimal(alt_str)
        alt_norm = _quantized_str(alt_dec) if "." in alt_str else alt_str.lstrip("+")
        # ensure explicit sign
        if alt_dec < 0:
            alt_part = alt_norm if alt_norm.startswith("-") else f"-{alt_norm}"
        else:
            alt_part = f"+{alt_norm.lstrip('-+')}"
    return f"{lat_iso}{lon_iso}{alt_part}/"


def _format_dms(lat_str: str, lon_str: str) -> str:
    deg_lat, min_lat, sec_lat, hemi_lat = _decimal_to_dms_parts(lat_str, True)
    deg_lon, min_lon, sec_lon, hemi_lon = _decimal_to_dms_parts(lon_str, False)
    return (
        f"{deg_lat}\u00b0{min_lat}\u2032{sec_lat}\u2033{hemi_lat} "
        f"{deg_lon}\u00b0{min_lon}\u2032{sec_lon}\u2033{hemi_lon}"
    )


def _format_dm(lat_str: str, lon_str: str) -> str:
    deg_lat, minutes_lat_q, hemi_lat = _decimal_to_dm_parts(lat_str, True)
    deg_lon, minutes_lon_q, hemi_lon = _decimal_to_dm_parts(lon_str, False)
    lat_min_str = format(minutes_lat_q.normalize(), "f") if minutes_lat_q != 0 else "0"
    lon_min_str = format(minutes_lon_q.normalize(), "f") if minutes_lon_q != 0 else "0"
    if "." not in lat_min_str:
        lat_min_str += ".0"
    if "." not in lon_min_str:
        lon_min_str += ".0"
    return (
        f"{deg_lat}\u00b0{lat_min_str}\u2032{hemi_lat} "
        f"{deg_lon}\u00b0{lon_min_str}\u2032{hemi_lon}"
    )


class CoordinatesCapability(Capability[CoordinatesNotation]):
    """Coordinates canonicalization capability — WGS 84."""

    name = "coordinates"

    def get_grammars(self) -> list[Grammar[CoordinatesNotation]]:
        return [CoordinatesRecognitionGrammar()]

    def get_rules(self) -> list[Rule[CoordinatesNotation]]:
        return [
            Section6CoordinateStructure(),
            SectionAnnexHStringExpression(),
            Section33GeoUriValidity(),
            Section311Position(),
        ]

    @staticmethod
    def create_contract(
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

    def format_value(
        self, value: str, output_format: str | None, notation: CoordinatesNotation
    ) -> str:
        lat = notation.latitude
        lon = notation.longitude
        alt = notation.altitude
        fmt = output_format or "decimal"
        if fmt == "decimal":
            return value
        if fmt == "iso6709":
            return _format_iso(lat, lon, alt)
        if fmt == "geo_uri":
            base = f"geo:{lat},{lon}"
            if alt is not None:
                base += f",{alt}"
            return base
        if fmt == "geojson_pair":
            if alt is not None:
                return f"[{lon}, {lat}, {alt}]"
            return f"[{lon}, {lat}]"
        if fmt == "dms":
            dms = _format_dms(lat, lon)
            if alt is not None:
                dms += f", {alt}"
            return dms
        if fmt == "dm":
            dm = _format_dm(lat, lon)
            if alt is not None:
                dm += f", {alt}"
            return dm
        return value
