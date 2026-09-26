"""Tests for ISNINotation."""

import dataclasses

import pytest

from paxman.capabilities.ISNI.notation import ISNINotation


@pytest.mark.capability
class TestISNINotation:
    """ISNI notation carries the normalized spaced display plus fields."""

    def test_field_invariants(self) -> None:
        n = ISNINotation(
            compact="0000000121032683",
            spaced="0000 0001 2103 2683",
            uri="https://isni.org/isni/0000000121032683",
            check="3",
            is_uri="false",
        )
        assert n.compact == "0000000121032683"
        assert n.spaced == "0000 0001 2103 2683"
        assert n.spaced.replace(" ", "") == n.compact
        assert n.check == n.compact[15]
        assert n.uri == "https://isni.org/isni/" + n.compact

    def test_frozen_slots_hashable(self) -> None:
        n = ISNINotation(
            compact="0000000121032683",
            spaced="0000 0001 2103 2683",
            uri="https://isni.org/isni/0000000121032683",
            check="3",
            is_uri="false",
        )
        with pytest.raises(dataclasses.FrozenInstanceError):
            n.compact = "other"  # type: ignore[misc]
        assert ISNINotation.__dataclass_params__.slots is True
        assert hash(n) == hash(
            ISNINotation(
                compact="0000000121032683",
                spaced="0000 0001 2103 2683",
                uri="https://isni.org/isni/0000000121032683",
                check="3",
                is_uri="false",
            )
        )
