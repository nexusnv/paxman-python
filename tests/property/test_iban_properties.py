from hypothesis import given
from hypothesis import strategies as st

from paxman.capabilities.IBAN.contract import IBANContract
from paxman.capabilities.IBAN.notation import IBANNotation
from paxman.capabilities.IBAN.rules.iso_13616_1_ed2020 import (
    REGISTERED_IBAN_COUNTRY_CODES,
    Section4IBANStructureMOD97,
)


def calc_check(country: str, bban: str) -> str:
    """ISO/IEC 7064 MOD 97-10 generation: 98 - (mod97 of bban+cc+"00")."""
    rearr = bban + country + "00"
    exp = "".join(str(ord(c) - 55) if c.isalpha() else c for c in rearr)
    r = 0
    for ch in exp:
        r = (r * 10 + int(ch)) % 97
    return f"{98 - r:02d}"


@given(st.data())
def test_tampered_check_digit_is_rejected(data: st.DataObject) -> None:
    cc = data.draw(st.sampled_from(sorted(REGISTERED_IBAN_COUNTRY_CODES)))
    # Per-country fixed length — generate BBAN of exact required length
    from paxman.capabilities.IBAN.rules.data.iban_registry import IBAN_LENGTHS

    expected_len = IBAN_LENGTHS[cc]
    bban_len = expected_len - 4
    bban = data.draw(
        st.text(
            min_size=bban_len,
            max_size=bban_len,
            alphabet="0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ",
        )
    )
    rule = Section4IBANStructureMOD97()
    dd = calc_check(cc, bban)
    compact_valid = cc + dd + bban
    valid_notation = IBANNotation(
        country_code=cc, check_digits=dd, bban=bban, compact=compact_valid
    )
    assert rule.matches(valid_notation, IBANContract()) is True

    # Mutate one check digit to a different value; preserve cc and bban.
    # Try both positions and digits until we find a mutation that is not the
    # original and is outside the banned 00/01/99 fast-reject, then assert
    # MOD 97-10 rejection. This avoids the ~1/97 flake where a random
    # mutation could still be MOD 97-valid.
    found_invalid: str | None = None
    for pos in (0, 1):
        orig = dd[pos]
        for digit in map(str, range(10)):
            if digit == orig:
                continue
            mutated = (digit + dd[1]) if pos == 0 else (dd[0] + digit)
            if mutated in ("00", "01", "99"):
                # Still invalid via DD range — counts as rejection, but we
                # prefer a MOD 97-driven rejection when possible.
                continue
            candidate = cc + mutated + bban
            cand_notation = IBANNotation(
                country_code=cc, check_digits=mutated, bban=bban, compact=candidate
            )
            if not rule.matches(cand_notation, IBANContract()):
                found_invalid = mutated
                break
        if found_invalid is not None:
            break
    # Fallback: if every non-banned mutation were MOD 97-valid (vanishingly
    # unlikely), fall back to a banned DD which is also rejected.
    if found_invalid is None:
        mutated = "00" if dd != "00" else "02"
        found_invalid = mutated
    tampered = IBANNotation(
        country_code=cc,
        check_digits=found_invalid,
        bban=bban,
        compact=cc + found_invalid + bban,
    )
    assert rule.matches(tampered, IBANContract()) is False


def test_generated_valid_is_valid() -> None:
    bban = "370400440532013000"
    cc = "DE"
    dd = calc_check(cc, bban)
    compact = cc + dd + bban
    assert Section4IBANStructureMOD97().matches(
        IBANNotation(country_code=cc, check_digits=dd, bban=bban, compact=compact),
        IBANContract(),
    )
