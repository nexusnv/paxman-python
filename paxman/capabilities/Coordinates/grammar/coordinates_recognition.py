"""Coordinates recognition grammar — pair + carriers."""

from __future__ import annotations

import re
from decimal import ROUND_HALF_EVEN, Decimal, InvalidOperation

from paxman.capabilities.Coordinates.notation import CoordinatesNotation
from paxman.core.grammar.boundary import BoundaryGuard
from paxman.core.grammar.pipeline import PipelineGrammar
from paxman.core.grammar.stages import RegexStage, StandardPre

_DEC = r"\d{1,3}(?:\.\d{1,7})?"
_SEP = r"[\s,;/]+"
_GEO_COORD = r"[+-]?\d{1,3}(?:\.\d+)?"

# Carrier bodies (module-scope strings, uncompiled)
_GEO_BODY_CORE = (
    rf"geo:{_GEO_COORD},{_GEO_COORD}"
    rf"(?:,{_GEO_COORD})?"
    rf"(?:;(?:crs=wgs84|u=\d+(?:\.\d+)?))*"
)
_GEO_BODY = rf"(?P<geo>{_GEO_BODY_CORE})(?![\d.])(?!;crs=)"

_ISO_BODY = (
    r"(?P<iso>[+-]\d{2,7}(?:\.\d+)?"
    r"[+-]\d{2,8}(?:\.\d+)?"
    r"(?:[+-]\d+(?:\.\d+)?)?"
    r"(?:CRS[A-Za-z0-9_]+)?/?)"
)

_JSON_BODY = (
    r"(?P<geojson>\[\s*[+-]?\d{1,3}(?:\.\d+)?"
    r"\s*,\s*[+-]?\d{1,3}(?:\.\d+)?"
    r"(?:\s*,\s*[+-]?\d+(?:\.\d+)?)?\s*\])"
)

# Pair branch — hemisphere front/back, DMS units, optional parens
_HEMI_FRONT_LAT = r"(?P<hemi_front_lat>[NSEWnsew])?[\s:]*"
_HEMI_FRONT_LON = r"(?P<hemi_front_lon>[NSEWnsew])?[\s:]*"
_SIGN_LAT = r"(?P<sign_lat>[-+])?"
_SIGN_LON = r"(?P<sign_lon>[-+])?"
_DEG_LAT = r"(?P<deg_lat>\d{1,3}(?:\.\d{1,7})?)"
_DEG_LON = r"(?P<deg_lon>\d{1,3}(?:\.\d{1,7})?)"

# DMS suffixes — degree symbol or whitespace required before minutes, plus '' handling
_DMS_LAT = (
    r"(?:(?:\s*[°\u00B0D\*]\s*|\s+)"
    r"(?P<min_lat>\d{1,2}(?:\.\d+)?)\s*(?:[′\u2032'm])?"
    r"(?:\s*(?P<sec_lat>\d{1,2}(?:\.\d+)?)\s*(?:''|[″\u2033\"s])\s*(?P<sec_frac_lat>\d+)?)?"
    r")?"
)
_DMS_LON = (
    r"(?:(?:\s*[°\u00B0D\*]\s*|\s+)"
    r"(?P<min_lon>\d{1,2}(?:\.\d+)?)\s*(?:[′\u2032'm])?"
    r"(?:\s*(?P<sec_lon>\d{1,2}(?:\.\d+)?)\s*(?:''|[″\u2033\"s])\s*(?P<sec_frac_lon>\d+)?)?"
    r")?"
)

_HEMI_BACK_LAT = r"(?:\s*(?P<hemi_back_lat>[NSEWnsew]))?"
_HEMI_BACK_LON = r"(?:\s*(?P<hemi_back_lon>[NSEWnsew]))?"

_COMP_LAT = f"{_HEMI_FRONT_LAT}{_SIGN_LAT}{_DEG_LAT}{_DMS_LAT}{_HEMI_BACK_LAT}"
_COMP_LON = f"{_HEMI_FRONT_LON}{_SIGN_LON}{_DEG_LON}{_DMS_LON}{_HEMI_BACK_LON}"

_PAIR_SEP = rf"(?:{_SEP}|(?<=[NSEWnsew])(?=\d))"
_PAIR_INNER = rf"{_COMP_LAT}\s*{_PAIR_SEP}\s*{_COMP_LON}"
# Prevent pair inside geo: URI (foreign CRS → no pair)
_PAIR_BODY = rf"(?P<pair>(?:\(\s*)?(?<![Gg][Ee][Oo]:){_PAIR_INNER}(?:\s*\))?)"

_BODY_ALTS = f"{_GEO_BODY}|{_ISO_BODY}|{_JSON_BODY}|(?:{_PAIR_BODY})"
_COORDS_BODY = rf"(?ai:(?:(?:COORDS?|LAT(?:\/LON)?)[\s:-]+)?(?P<core>{_BODY_ALTS}))"
_GUARD = BoundaryGuard.word_only()
# Extra exclusions: % (research §2.3) and \.\d truncation (geo foreign, pair+percent)
_COORDS_PATTERN = (
    _GUARD.lookbehind + _COORDS_BODY + r"(?!\.\d)(?![%])" + _GUARD.lookahead
)


def _quantize(v: Decimal) -> str:
    q = v.quantize(Decimal("0.000001"), rounding=ROUND_HALF_EVEN).normalize()
    if q == 0:
        q = Decimal(0)
    return format(q, "f")


def _normalize_alt(s: str) -> str:
    d = Decimal(s)
    nd = d.normalize()
    if nd == 0:
        nd = Decimal(0)
    return format(nd, "f")


def _iso_component_to_decimal(val_str: str, is_lat: bool) -> Decimal:
    if "." in val_str:
        int_part, frac_part = val_str.split(".", 1)
        frac = "." + frac_part
    else:
        int_part = val_str
        frac = ""
    # lat uses 2-digit degrees, lon 3-digit
    if is_lat:
        if len(int_part) == 2:
            return Decimal(int_part + frac)
        elif len(int_part) == 4:
            deg = Decimal(int_part[0:2])
            minutes = Decimal(int_part[2:4] + frac)
            return deg + minutes / Decimal(60)
        elif len(int_part) == 6:
            deg = Decimal(int_part[0:2])
            minutes = Decimal(int_part[2:4])
            seconds = Decimal(int_part[4:6] + frac)
            return deg + minutes / Decimal(60) + seconds / Decimal(3600)
        else:
            try:
                return Decimal(val_str)
            except Exception:
                return Decimal(0)
    else:
        if len(int_part) == 3:
            return Decimal(int_part + frac)
        elif len(int_part) == 5:
            deg = Decimal(int_part[0:3])
            minutes = Decimal(int_part[3:5] + frac)
            return deg + minutes / Decimal(60)
        elif len(int_part) == 7:
            deg = Decimal(int_part[0:3])
            minutes = Decimal(int_part[3:5])
            seconds = Decimal(int_part[5:7] + frac)
            return deg + minutes / Decimal(60) + seconds / Decimal(3600)
        else:
            try:
                return Decimal(val_str)
            except Exception:
                return Decimal(0)


def _is_contradictory(hemi: str | None, sign: str | None) -> bool:
    """Return True when sign and hemisphere contradict.

    Hemisphere S/W implies negative, N/E implies positive.
    Sign '-' implies negative, '+' or absent implies positive.
    Contradiction when the implied signs differ and both are present.
    """
    if hemi is None or sign is None:
        return False
    hemi_up = hemi.upper()
    hemi_negative = hemi_up in ("S", "W")
    sign_negative = sign == "-"
    # sign '+' is explicit positive, also contradictory with S/W
    # if sign is '+' and hemi is S/W => contradictory
    # if sign is '-' and hemi is N/E => contradictory
    return hemi_negative != sign_negative


def _dms_overflow(min_str: str | None, sec_str: str | None) -> bool:
    """Return True when minutes or seconds are >=60."""
    try:
        if min_str is not None and Decimal(min_str) >= Decimal(60):
            return True
        if sec_str is not None and Decimal(sec_str) >= Decimal(60):
            return True
    except (InvalidOperation, ValueError):
        return False
    return False


def _iso_width_invalid(lat_val: str, lon_val: str) -> tuple[bool, bool]:
    """Check ISO 6709 integer digit widths.

    Returns (lat_invalid, lon_invalid).
    """
    lat_int = lat_val.split(".", 1)[0] if "." in lat_val else lat_val
    lon_int = lon_val.split(".", 1)[0] if "." in lon_val else lon_val
    lat_invalid = len(lat_int) not in (2, 4, 6)
    lon_invalid = len(lon_int) not in (3, 5, 7)
    return lat_invalid, lon_invalid


def _notation(match: re.Match[str]) -> CoordinatesNotation:
    gd = match.groupdict()
    # Geo branch
    if gd.get("geo") is not None:
        geo_raw = gd["geo"]
        # split off scheme
        colon = geo_raw.find(":")
        body = geo_raw[colon + 1 :] if colon != -1 else geo_raw
        # split coords vs params
        parts = body.split(";")
        coords_part = parts[0]
        coords = coords_part.split(",")
        lat_raw = coords[0]
        lon_raw = coords[1] if len(coords) > 1 else "0"
        alt_raw = coords[2] if len(coords) > 2 else None
        lat_dec = Decimal(lat_raw)
        lon_dec = Decimal(lon_raw)
        lat_q = _quantize(lat_dec)
        lon_q = _quantize(lon_dec)
        alt_norm = _normalize_alt(alt_raw) if alt_raw is not None else None
        compact = f"{lat_q}, {lon_q}"
        if alt_norm is not None:
            compact += f", {alt_norm}"
        return CoordinatesNotation(
            latitude=lat_q,
            longitude=lon_q,
            altitude=alt_norm,
            coord_shape="geo_uri",
            compact=compact,
        )
    if gd.get("iso") is not None:
        iso_raw = gd["iso"]
        # iso_raw like +48.52+002.20/  or +27.5916+086.5640+8850CRSWGS_84/
        has_solidus = iso_raw.endswith("/")
        core = iso_raw[:-1] if has_solidus else iso_raw
        # detect CRS suffix if present (case-insensitive)
        crs_label: str | None = None
        crs_match = re.search(r"(?i)CRS[A-Za-z0-9_]*", core)
        if crs_match:
            crs_label = core[crs_match.start() :]
            core = core[: crs_match.start()]
        # Parse signed components via regex
        # pattern: [+-]val [+-]val [+-]val?
        comp_pat = re.compile(r"([+-])(\d+(?:\.\d+)?)")
        comps = comp_pat.findall(core)
        # comps is list of (sign, val)
        # Expected 2 or 3 comps
        if len(comps) >= 2:
            lat_sign, lat_val = comps[0]
            lon_sign, lon_val = comps[1]
            alt_sign = None
            alt_val = None
            alt_raw = None
            if len(comps) >= 3:
                alt_sign, alt_val = comps[2]
                alt_raw = f"{alt_sign}{alt_val}"
        else:
            # Fallback
            lat_sign, lat_val = "+", "0"
            lon_sign, lon_val = "+", "0"
            alt_raw = None
        # structural width check — encode invalid as out-of-range sentinel
        lat_width_invalid, lon_width_invalid = _iso_width_invalid(lat_val, lon_val)
        lat_dec_unsigned = _iso_component_to_decimal(lat_val, is_lat=True)
        lon_dec_unsigned = _iso_component_to_decimal(lon_val, is_lat=False)
        lat_dec = -lat_dec_unsigned if lat_sign == "-" else lat_dec_unsigned
        lon_dec = -lon_dec_unsigned if lon_sign == "-" else lon_dec_unsigned
        # if width invalid, force out-of-range so rule's range check rejects
        if lat_width_invalid:
            lat_dec = Decimal("91") if lat_dec >= 0 else Decimal("-91")
        if lon_width_invalid:
            lon_dec = Decimal("181") if lon_dec >= 0 else Decimal("-181")
        # Annex H: missing trailing solidus → INVALID; foreign CRS → INVALID
        crs_invalid = False
        if not has_solidus:
            crs_invalid = True
        elif crs_label is not None:
            upper = crs_label.upper()
            if upper not in ("CRSWGS_84", "CRSWGS84"):
                crs_invalid = True
        if crs_invalid:
            # encode as out-of-range lat for rule rejection (covers both cases)
            lat_dec = Decimal("91") if lat_dec >= 0 else Decimal("-91")
        lat_q = _quantize(lat_dec)
        lon_q = _quantize(lon_dec)
        alt_norm = _normalize_alt(alt_raw) if alt_raw is not None else None
        compact = f"{lat_q}, {lon_q}"
        if alt_norm is not None:
            compact += f", {alt_norm}"
        return CoordinatesNotation(
            latitude=lat_q,
            longitude=lon_q,
            altitude=alt_norm,
            coord_shape="iso6709",
            compact=compact,
        )
    if gd.get("geojson") is not None:
        gj_raw = gd["geojson"]
        inner = gj_raw.strip()[1:-1]
        parts = [p.strip() for p in inner.split(",")]
        lon_raw = parts[0] if len(parts) > 0 else "0"
        lat_raw = parts[1] if len(parts) > 1 else "0"
        alt_raw = parts[2] if len(parts) > 2 else None
        lat_dec = Decimal(lat_raw)
        lon_dec = Decimal(lon_raw)
        lat_q = _quantize(lat_dec)
        lon_q = _quantize(lon_dec)
        alt_norm = _normalize_alt(alt_raw) if alt_raw is not None else None
        compact = f"{lat_q}, {lon_q}"
        if alt_norm is not None:
            compact += f", {alt_norm}"
        return CoordinatesNotation(
            latitude=lat_q,
            longitude=lon_q,
            altitude=alt_norm,
            coord_shape="geojson",
            compact=compact,
        )
    # Pair branch
    # Extract lat/lon groups
    hemi_front_lat = gd.get("hemi_front_lat")
    hemi_back_lat = gd.get("hemi_back_lat")
    hemi_lat = hemi_front_lat or hemi_back_lat
    sign_lat = gd.get("sign_lat")
    deg_lat = gd.get("deg_lat") or "0"
    min_lat = gd.get("min_lat")
    sec_lat = gd.get("sec_lat")
    sec_frac_lat = gd.get("sec_frac_lat")

    hemi_front_lon = gd.get("hemi_front_lon")
    hemi_back_lon = gd.get("hemi_back_lon")
    hemi_lon = hemi_front_lon or hemi_back_lon
    sign_lon = gd.get("sign_lon")
    deg_lon = gd.get("deg_lon") or "0"
    min_lon = gd.get("min_lon")
    sec_lon = gd.get("sec_lon")
    sec_frac_lon = gd.get("sec_frac_lon")

    # shape discriminator
    has_sec = sec_lat is not None or sec_lon is not None
    has_min = min_lat is not None or min_lon is not None
    if has_sec:
        shape = "dms"
    elif has_min:
        shape = "ddm"
    else:
        shape = "dd"

    # structural checks that must be rule-rejected: encode as out-of-range
    lat_contradiction = _is_contradictory(hemi_lat, sign_lat)
    lon_contradiction = _is_contradictory(hemi_lon, sign_lon)
    lat_overflow = _dms_overflow(min_lat, sec_lat)
    lon_overflow = _dms_overflow(min_lon, sec_lon)
    # sec_frac overflow: if sec is present and sec_frac present, the effective
    # seconds value is sec.sec_frac ; sec_str <60 ensures overflow detection
    # For sec_frac "123" meaning 26.123 seconds, integer part 26 <60
    # so not overflow. Degenerate "26''123" splits as sec_lat="26",
    # sec_frac_lat="123" which is 26.123 seconds <60, valid.

    def _component_decimal(
        deg_str: str,
        min_str: str | None,
        sec_str: str | None,
        sec_frac: str | None,
        hemi: str | None,
        sign: str | None,
    ) -> Decimal:
        # deg_str is unsigned digits maybe with dot (for dd)
        # For DMS case, deg_str is integer without fraction, but we treat generically
        # Determine base magnitude
        if min_str is None and sec_str is None:
            # decimal degrees
            base = Decimal(deg_str)
        else:
            # DMS/DDM – deg is integer part, ignore any fraction in deg_str if present
            deg_part = deg_str.split(".")[0] if "." in deg_str else deg_str
            base = Decimal(deg_part)
            if min_str is not None:
                base += Decimal(min_str) / Decimal(60)
            if sec_str is not None:
                sec_val_str = sec_str
                if sec_frac is not None and "." not in sec_val_str:
                    sec_val_str = f"{sec_val_str}.{sec_frac}"
                # if sec already has dot, ignore sec_frac
                base += Decimal(sec_val_str) / Decimal(3600)
        # Apply sign via hemisphere or explicit sign
        if hemi is not None:
            hemi_up = hemi.upper()
            if hemi_up in ("S", "W"):
                return -abs(base)
            else:
                return abs(base)
        else:
            if sign == "-":
                return -abs(base)
            else:
                return abs(base)

    lat_dec = _component_decimal(
        deg_lat,
        min_lat,
        sec_lat,
        sec_frac_lat,
        hemi_lat,
        sign_lat,
    )
    lon_dec = _component_decimal(
        deg_lon,
        min_lon,
        sec_lon,
        sec_frac_lon,
        hemi_lon,
        sign_lon,
    )
    # encode structural invalidities as out-of-range sentinels for rule rejection
    if lat_contradiction or lat_overflow:
        lat_dec = Decimal("91") if lat_dec >= 0 else Decimal("-91")
    if lon_contradiction or lon_overflow:
        lon_dec = Decimal("181") if lon_dec >= 0 else Decimal("-181")

    lat_q = _quantize(lat_dec)
    lon_q = _quantize(lon_dec)
    compact = f"{lat_q}, {lon_q}"
    return CoordinatesNotation(
        latitude=lat_q,
        longitude=lon_q,
        altitude=None,
        coord_shape=shape,
        compact=compact,
    )


class CoordinatesRecognitionGrammar(PipelineGrammar[CoordinatesNotation]):
    name = "coordinates_recognition"
    semantics = "coordinates_recognition"
    single_value = True
    pre = StandardPre[CoordinatesNotation](empty_guard=True)
    regex = RegexStage[CoordinatesNotation](
        pattern=_COORDS_PATTERN, notation_fn=_notation
    )


# Backwards-compat alias for scaffold imports
CoordinatesRecognition = CoordinatesRecognitionGrammar
