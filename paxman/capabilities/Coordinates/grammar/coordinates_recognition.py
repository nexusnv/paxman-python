"""Coordinates recognition grammar — pair + carriers.

Recognition records *facts*, never verdicts: structural observations
(hemisphere/sign contradiction, DMS unit overflow, ISO 6709 digit width,
missing Annex H solidus, foreign CRS label, hemisphere axis mismatch) are
recorded on ``CoordinatesNotation.defects`` and the rules own every
accept/reject decision. Recognized values always faithfully represent the
input — no sentinel values are fabricated.

Boundary decisions (review-hardened):
- A match may never start after ``.`` or ``+``/``-`` glue — a dotted
  non-coordinate such as ``192.168.1.1`` cannot yield a mid-number match.
- A whitespace-only pair separator requires an affinity marker (hemisphere
  letter or sign) on BOTH components; bare prose number runs (``pages 12
  40``, phone numbers) stay unrecognized. Explicit ``,`` ``;`` ``/``
  separators keep the permissive attested surface (research §2.1 row 1).
- A ``geo:``-prefixed tail is never salvaged by the pair branch; invalid
  geo-URI tails (``;u=-10``, non-numeric altitude) are not recognized.
- A CRS label other than the WGS 84 family is recognized (so the rule can
  attribute the rejection) but rejected → INVALID — no silent datum
  transform (locked decision 6).

Documented v1 deviations from the research inventory: fraction digit runs
are capped at 7 (canonical quantum is 6 dp — an 8+-digit fraction is
MISSING, not quantized); a single component with contradictory hemisphere
(``-41.5 N``) is MISSING because the pair is the unit of identity; four
numeric components resolve as two distinct mentions; per-component
``Lat:``/``Lon:`` labels are deferred.
"""

from __future__ import annotations

import re
from decimal import ROUND_HALF_EVEN, Decimal, InvalidOperation

from paxman.capabilities.Coordinates.notation import CoordinatesNotation
from paxman.core.grammar.boundary import BoundaryGuard
from paxman.core.grammar.pipeline import PipelineGrammar
from paxman.core.grammar.stages import RegexStage, StandardPre

_GEO_COORD = r"[+-]?\d{1,3}(?:\.\d+)?"

# Carrier bodies (module-scope strings, uncompiled)
_GEO_BODY_CORE = (
    rf"geo:{_GEO_COORD},{_GEO_COORD}"
    rf"(?:,{_GEO_COORD})?"
    rf"(?:;u=\d+(?:\.\d+)?|;crs=[A-Za-z0-9_\-]+)*"
)
_GEO_BODY = rf"(?P<geo>{_GEO_BODY_CORE})(?![\d.,])(?!;u=)"

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


def _component(side: str, sfx: str = "") -> str:
    """Capturing pair-component pattern for *side* ("lat" or "lon").

    ``sfx`` suffixes the group names: the whitespace-separator alternative
    uses ``_w``-suffixed groups so the two pair alternatives never
    redefine a group name.
    """
    hemi_front = rf"(?P<hemi_front_{side}{sfx}>[NSEWnsew])?[\s:]*"
    sign = rf"(?P<sign_{side}{sfx}>[-+])?"
    deg = rf"(?P<deg_{side}{sfx}>\d{{1,3}}(?:\.\d{{1,7}})?)"
    dms = (
        r"(?:(?:\s*[°\u00B0D\*]\s*|\s+)"
        rf"(?P<min_{side}{sfx}>\d{{1,2}}(?:\.\d+)?)\s*(?:[′\u2032'm])?"
        rf"(?:\s*(?P<sec_{side}{sfx}>\d{{1,2}}(?:\.\d+)?)\s*"
        rf"(?:''|[″\u2033\"s])\s*(?P<sec_frac_{side}{sfx}>\d+)?)?"
        r")?"
    )
    hemi_back = rf"(?:\s*(?P<hemi_back_{side}{sfx}>[NSEWnsew]))?"
    return f"{hemi_front}{sign}{deg}{dms}{hemi_back}"


_COMP_LAT = _component("lat")
_COMP_LON = _component("lon")
_COMP_LAT_W = _component("lat", "_w")
_COMP_LON_W = _component("lon", "_w")

# Non-capturing sketch of one component — used only inside the
# whitespace-affinity lookahead, so it carries no group names.
_NC_COMP = (
    r"[-+]?\d{1,3}(?:\.\d{1,7})?"
    r"(?:(?:\s*[°\u00B0D\*]\s*|\s+)"
    r"\d{1,2}(?:\.\d+)?\s*[′\u2032'm]?"
    r"(?:\s*\d{1,2}(?:\.\d+)?\s*(?:''|[″\u2033\"s])\s*\d*)?"
    r")?"
)
# A "marked" component carries an affinity marker: a front hemisphere
# letter, a sign, or a back hemisphere letter.
_NC_MARKED = (
    rf"(?:[NSEWnsew][\s:]*{_NC_COMP}(?:\s*[NSEWnsew])?"
    rf"|[-+]{_NC_COMP}(?:\s*[NSEWnsew])?"
    rf"|{_NC_COMP}\s*[NSEWnsew])"
)

# Explicit separator (contains , ; or /): no affinity required — the bare
# decimal pair (research §2.1 row 1) is the canonical surface. The
# zero-width alternative keeps degenerate no-space DMS (row 14) matchable.
_SEP_EXPLICIT = r"(?:\s*[,;/][\s,;/]*|(?<=[NSEWnsew])(?=\d))"
# Whitespace-only separator: BOTH components must be marked, otherwise any
# two adjacent prose numbers would claim coordinate status.
_SEP_WS = r"(?:\s+|(?<=[NSEWnsew])(?=\d))"

_PAIR_EXPLICIT = rf"{_COMP_LAT}\s*{_SEP_EXPLICIT}\s*{_COMP_LON}"
_PAIR_WS = (
    rf"(?={_NC_MARKED}{_SEP_WS}{_NC_MARKED})"
    rf"{_COMP_LAT_W}\s*{_SEP_WS}\s*{_COMP_LON_W}"
)
# The pair branch never salvages the tail of a geo: URI.
_PAIR_BODY = rf"(?P<pair>(?:\(\s*)?(?<!geo:)(?:{_PAIR_EXPLICIT}|{_PAIR_WS})(?:\s*\))?)"

_BODY_ALTS = f"{_GEO_BODY}|{_ISO_BODY}|{_JSON_BODY}|(?:{_PAIR_BODY})"
_COORDS_BODY = rf"(?ai:(?:(?:COORDS?|LAT(?:\/LON)?)[\s:-]+)?(?P<core>{_BODY_ALTS}))"
_GUARD = BoundaryGuard.word_only()
# Extra exclusions: % suffix (research §2.3), trailing fraction truncation,
# and leading glue — a match may not start after a dot or a sign character.
_COORDS_PATTERN = (
    _GUARD.lookbehind
    + r"(?<!\.)(?<![-+])"
    + _COORDS_BODY
    + r"(?!\.\d)(?![%])"
    + _GUARD.lookahead
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
            except (InvalidOperation, ValueError):
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
            except (InvalidOperation, ValueError):
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
        # RFC 5870 §3.4.1: crs must be absent or wgs84 (case-insensitive);
        # any other datum is recorded so the rule can reject (no silent
        # datum transform — locked decision 6).
        crs_label: str | None = None
        for param in parts[1:]:
            if param.lower().startswith("crs="):
                crs_label = param[4:]
        defects: list[str] = []
        if crs_label is not None and crs_label.lower() not in ("wgs84", "wgs_84"):
            defects.append("foreign_crs")
        return CoordinatesNotation(
            latitude=lat_q,
            longitude=lon_q,
            altitude=alt_norm,
            coord_shape="geo_uri",
            compact=compact,
            defects=tuple(defects),
        )
    if gd.get("iso") is not None:
        iso_raw = gd["iso"]
        # iso_raw like +48.52+002.20/  or +27.5916+086.5640+8850CRSWGS_84/
        has_solidus = iso_raw.endswith("/")
        core = iso_raw[:-1] if has_solidus else iso_raw
        # detect CRS suffix if present (case-insensitive)
        crs_label = None
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
            if len(comps) >= 3:
                alt_sign, alt_val = comps[2]
                alt_raw = f"{alt_sign}{alt_val}"
            else:
                alt_sign, alt_val, alt_raw = None, None, None
        else:
            # Fallback
            lat_sign, lat_val = "+", "0"
            lon_sign, lon_val = "+", "0"
            alt_raw = None
        # Record structural facts; the values stay faithful to the input.
        lat_width_invalid, lon_width_invalid = _iso_width_invalid(lat_val, lon_val)
        defects = []
        if lat_width_invalid or lon_width_invalid:
            defects.append("iso_digit_width")
        if not has_solidus:
            defects.append("iso_missing_solidus")
        elif crs_label is not None:
            upper = crs_label.upper()
            if upper not in ("CRSWGS_84", "CRSWGS84"):
                defects.append("foreign_crs")
        lat_dec_unsigned = _iso_component_to_decimal(lat_val, is_lat=True)
        lon_dec_unsigned = _iso_component_to_decimal(lon_val, is_lat=False)
        lat_dec = -lat_dec_unsigned if lat_sign == "-" else lat_dec_unsigned
        lon_dec = -lon_dec_unsigned if lon_sign == "-" else lon_dec_unsigned
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
            defects=tuple(defects),
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
            defects=(),
        )

    # Pair branch
    # The two pair alternatives use distinct group-name sets (the
    # whitespace-separator alternative suffixes its groups with "_w");
    # read whichever set matched.
    def _pg(name: str) -> str | None:
        value = gd.get(name)
        return value if value is not None else gd.get(f"{name}_w")

    # Extract lat/lon groups
    hemi_front_lat = _pg("hemi_front_lat")
    hemi_back_lat = _pg("hemi_back_lat")
    hemi_lat = hemi_front_lat or hemi_back_lat
    sign_lat = _pg("sign_lat")
    deg_lat = _pg("deg_lat") or "0"
    min_lat = _pg("min_lat")
    sec_lat = _pg("sec_lat")
    sec_frac_lat = _pg("sec_frac_lat")

    hemi_front_lon = _pg("hemi_front_lon")
    hemi_back_lon = _pg("hemi_back_lon")
    hemi_lon = hemi_front_lon or hemi_back_lon
    sign_lon = _pg("sign_lon")
    deg_lon = _pg("deg_lon") or "0"
    min_lon = _pg("min_lon")
    sec_lon = _pg("sec_lon")
    sec_frac_lon = _pg("sec_frac_lon")

    # shape discriminator
    has_sec = sec_lat is not None or sec_lon is not None
    has_min = min_lat is not None or min_lon is not None
    if has_sec:
        shape = "dms"
    elif has_min:
        shape = "ddm"
    else:
        shape = "dd"

    # Structural facts recorded for the rule layer (values stay faithful).
    lat_contradiction = _is_contradictory(hemi_lat, sign_lat)
    lon_contradiction = _is_contradictory(hemi_lon, sign_lon)
    lat_overflow = _dms_overflow(min_lat, sec_lat)
    lon_overflow = _dms_overflow(min_lon, sec_lon)
    defects = []
    if lat_contradiction or lon_contradiction:
        defects.append("sign_hemisphere_conflict")
    # Hemisphere letters must match their component's axis: N/S latitude,
    # E/W longitude. A mismatched letter has no authoritative reading.
    if (hemi_lat is not None and hemi_lat.upper() in ("E", "W")) or (
        hemi_lon is not None and hemi_lon.upper() in ("N", "S")
    ):
        defects.append("hemisphere_axis_mismatch")
    if lat_overflow or lon_overflow:
        defects.append("dms_unit_overflow")
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

    lat_q = _quantize(lat_dec)
    lon_q = _quantize(lon_dec)
    compact = f"{lat_q}, {lon_q}"
    return CoordinatesNotation(
        latitude=lat_q,
        longitude=lon_q,
        altitude=None,
        coord_shape=shape,
        compact=compact,
        defects=tuple(defects),
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
