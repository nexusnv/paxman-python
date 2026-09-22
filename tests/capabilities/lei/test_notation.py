"""Tests for LEINotation."""

import dataclasses

import pytest

from paxman.capabilities.LEI.notation import LEINotation


def _notation(compact: str) -> LEINotation:
    return LEINotation(
        lou_prefix=compact[0:4],
        entity_block=compact[4:18],
        check_digits=compact[18:20],
        compact=compact,
    )


@pytest.mark.capability
class TestLEINotation:
    """Tests for LEINotation."""

    def test_frozen_slots_hash(self) -> None:
        n = _notation("213800KUD8LAJWSQ9D15")
        with pytest.raises(dataclasses.FrozenInstanceError):
            n.compact = "5493000IBP32UQZ0KL24"  # type: ignore[misc]
        assert hash(n) == hash(_notation("213800KUD8LAJWSQ9D15"))
        # slots dataclass has no __dict__
        assert not hasattr(n, "__dict__")

    def test_compact_decomposition(self) -> None:
        n = _notation("213800KUD8LAJWSQ9D15")
        assert n.lou_prefix == "2138"
        assert n.entity_block == "00KUD8LAJWSQ9D"
        assert n.check_digits == "15"
        assert n.compact == "213800KUD8LAJWSQ9D15"
        assert n.compact == n.lou_prefix + n.entity_block + n.check_digits

    def test_zeros_preserved(self) -> None:
        n = _notation("5493000IBP32UQZ0KL24")
        assert n.lou_prefix == "5493"
        assert n.entity_block == "000IBP32UQZ0KL"
        assert n.check_digits == "24"
        assert n.compact == "5493000IBP32UQZ0KL24"

    def test_all_fields_str(self) -> None:
        n = _notation("7LTWFZYICNSX8D621K86")
        assert all(
            isinstance(v, str)
            for v in (n.lou_prefix, n.entity_block, n.check_digits, n.compact)
        )
