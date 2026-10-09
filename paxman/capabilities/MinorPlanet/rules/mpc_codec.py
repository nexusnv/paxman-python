"""MPC pack/unpack codec — rules-owned shared tables (never grammar).

Mirrors ``sbpy.data.Names.to_packed`` / ``from_packed`` arithmetic against
MPC PackedDes: century ``IJK`` = 18/19/20, cycle letter values
A=10..Z=35/a=36..z=61, tilde base-62 minus-620000, survey packs, and the
LSST-era extended ``_`` scheme. Pure functions returning ``None`` on
incoherent input (never raise); imported by rules and the capability only.
"""

from __future__ import annotations

_BASE62 = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"
_NO_I = "ABCDEFGHJKLMNOPQRSTUVWXYZ"
_HALF_MONTH = frozenset("ABCDEFGHJKLMNOPQRSTUVWXY")
_SECOND = frozenset("ABCDEFGHJKLMNOPQRSTUVWXYZ")

_BASE62_VALUE = {ch: i for i, ch in enumerate(_BASE62)}


def _base62_decode(s: str) -> int | None:
    """Decode a base-62 run; ``None`` on non-alphabet input."""
    total = 0
    for ch in s:
        v = _BASE62_VALUE.get(ch)
        if v is None:
            return None
        total = total * 62 + v
    return total


def _base62_encode(value: int, width: int) -> str | None:
    """Encode ``value`` as zero-padded base-62 of ``width``; ``None`` if wide."""
    if value < 0:
        return None
    digits = ["0"] * width
    for idx in range(width - 1, -1, -1):
        digits[idx] = _BASE62[value % 62]
        value //= 62
    if value != 0:
        return None
    return "".join(digits)


def mpc_unpack(spelled: str) -> str | None:
    """Decode a packed spelling to its canonical unpacked form (case-exact).

    Returns ``None`` for incoherent input (bad century, bad half-month,
    lowercase comet-fragment column 7). Caller decides lane by shape.
    """
    try:
        if len(spelled) == 5 and spelled.isdigit() and spelled.isascii():
            value = int(spelled)
            if value > 0:
                return f"({value})"
            return None
        if (
            len(spelled) == 5
            and spelled[0].isalpha()
            and spelled[0].isascii()
            and spelled[1:].isdigit()
            and spelled[1:].isascii()
        ):
            high = _BASE62_VALUE.get(spelled[0])
            if high is None or not 10 <= high <= 61:
                return None
            return f"({high}{spelled[1:]})"
        if (
            len(spelled) == 5
            and spelled.startswith("~")
            and spelled[1:].isascii()
            and all(ch in _BASE62_VALUE for ch in spelled[1:])
        ):
            tail = _base62_decode(spelled[1:])
            if tail is None:
                return None
            return f"({620000 + tail})"
        if spelled.startswith("PLS") and len(spelled) in (6, 7):
            num = spelled[3:]
            if num.isdigit() and num.isascii() and 1 <= int(num) <= 9999:
                return f"{int(num)} P-L"
            return None
        if (
            len(spelled) in (6, 7)
            and spelled[0] == "T"
            and spelled[1] in ("1", "2", "3")
            and spelled[2] == "S"
        ):
            num = spelled[3:]
            if num.isdigit() and num.isascii() and 1 <= int(num) <= 9999:
                return f"{int(num)} T-{spelled[1]}"
            return None
        if len(spelled) == 7 and spelled[0] == "_":
            year_letter, half, tail = spelled[1], spelled[2], spelled[3:]
            if (
                year_letter in _BASE62_VALUE
                and half in _HALF_MONTH
                and tail.isascii()
                and all(ch in _BASE62_VALUE for ch in tail)
            ):
                base = _base62_decode(tail)
                year_code = _BASE62_VALUE.get(year_letter)
                if base is None or year_code is None:
                    return None
                obj_num = 15501 + base
                second = _NO_I[(obj_num - 1) % 25]
                cycle = (obj_num - 1) // 25
                return f"20{year_code:02d} {half}{second}{cycle}"
            return None
        if (
            len(spelled) == 7
            and spelled[0].isalpha()
            and spelled[0].isascii()
            and spelled[1:3].isdigit()
            and spelled[1:3].isascii()
            and spelled[5].isdigit()
            and spelled[5].isascii()
        ):
            century = _BASE62_VALUE.get(spelled[0])
            half, col5, second = spelled[3], spelled[4], spelled[6]
            if century not in (18, 19, 20):
                return None
            if half not in _HALF_MONTH:
                return None
            if not second.isalpha() or not second.isascii() or not second.isupper():
                return None
            cycle_high = _BASE62_VALUE.get(col5)
            if cycle_high is None:
                return None
            cycle = f"{cycle_high}{spelled[5]}".lstrip("0")
            return f"{century}{spelled[1:3]} {half}{second}{cycle}"
        return None
    except (ValueError, IndexError, TypeError):
        return None


def mpc_pack(designation: str) -> str | None:
    """Encode a canonical unpacked designation to its packed form.

    Returns ``None`` when no packed mapping is defined (the ``A/`` lane)
    or the value is out of range. Case-exact output.
    """
    try:
        if designation.startswith("(") and designation.endswith(")"):
            inner = designation[1:-1]
            if not inner.isdigit() or not inner.isascii():
                return None
            n = int(inner)
            if n <= 0:
                return None
            if n < 100000:
                return f"{n:05d}"
            if n < 620000:
                return f"{_BASE62[n // 10000]}{n % 10000:04d}"
            if n <= 15396335:
                tail = _base62_encode(n - 620000, 4)
                return f"~{tail}" if tail is not None else None
            return None
        if designation.endswith("P-L") or designation[-3:] in (
            "T-1",
            "T-2",
            "T-3",
        ):
            head, _, survey = designation.partition(" ")
            if not head.isdigit() or not head.isascii():
                return None
            n = int(head)
            if not 1 <= n <= 9999:
                return None
            if survey == "P-L":
                return f"PLS{n:04d}"
            return f"T{survey[-1]}S{n:04d}"
        if designation.startswith("A/"):
            return None
        if (
            len(designation) >= 7
            and designation[:4].isdigit()
            and designation[:4].isascii()
            and designation[4] == " "
        ):
            year = designation[:4]
            if not (
                year.startswith(("19", "20"))
                or (year[0] == "A" and year[1] in "89" and year[2:].isdigit())
            ):
                return None
            rest = designation[5:]
            if len(rest) < 2 or rest[0] not in _HALF_MONTH or rest[1] not in _SECOND:
                return None
            half, second, num = rest[0], rest[1], rest[2:]
            if num and (not num.isdigit() or not num.isascii()):
                return None
            if num and num[0] == "0":
                # Degenerate cycle ("XA0", "TA05"): the packed field would
                # collapse the leading zero and fail to re-enter.
                return None
            # A-prefix retrospective years have no standard packing lane.
            if year[0] == "A":
                return None
            packed_year = _BASE62[int(year[:2])] + year[2:]
            if num == "":
                return f"{packed_year}{half}00{second}"
            if len(num) == 1:
                return f"{packed_year}{half}0{num}{second}"
            obj_num = int(num) * 25 + _NO_I.find(second) + 1
            if obj_num < 15501:
                return f"{packed_year}{half}{_BASE62[int(num[:-1])]}{num[-1]}{second}"
            if obj_num < 14791837:
                obj_num -= 15501
                tail = _base62_encode(obj_num, 4)
                if tail is None:
                    return None
                return f"_{_BASE62[int(year[2:])]}{half}{tail}"
            return None
        return None
    except (ValueError, IndexError, TypeError):
        return None
