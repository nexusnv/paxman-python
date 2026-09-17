"""Tests for UUIDNotation (RFC 9562 §4 carrier pre-computation)."""

import dataclasses

import pytest

from paxman.capabilities.UUID.notation import UUIDNotation


@pytest.mark.capability
class TestUUIDNotation:
    """Notation carries compact + pre-computed presentations (ORCID precedent)."""

    def test_fields(self) -> None:
        n = UUIDNotation(
            compact="6ba7b8109dad11d180b400c04fd430c8",
            hyphenated="6ba7b810-9dad-11d1-80b4-00c04fd430c8",
            urn="urn:uuid:6ba7b810-9dad-11d1-80b4-00c04fd430c8",
            version="1",
        )
        assert n.compact == "6ba7b8109dad11d180b400c04fd430c8"
        assert n.hyphenated == "6ba7b810-9dad-11d1-80b4-00c04fd430c8"
        assert n.urn == "urn:uuid:6ba7b810-9dad-11d1-80b4-00c04fd430c8"
        assert n.version == "1"

    def test_version_sentinels(self) -> None:
        nil = UUIDNotation(
            compact="0" * 32,
            hyphenated="00000000-0000-0000-0000-000000000000",
            urn="urn:uuid:00000000-0000-0000-0000-000000000000",
            version="nil",
        )
        assert nil.version == "nil"
        mx = UUIDNotation(
            compact="f" * 32,
            hyphenated="ffffffff-ffff-ffff-ffff-ffffffffffff",
            urn="urn:uuid:ffffffff-ffff-ffff-ffff-ffffffffffff",
            version="max",
        )
        assert mx.version == "max"

    def test_frozen_slots_hash(self) -> None:
        n = UUIDNotation(
            compact="6ba7b8109dad11d180b400c04fd430c8",
            hyphenated="6ba7b810-9dad-11d1-80b4-00c04fd430c8",
            urn="urn:uuid:6ba7b810-9dad-11d1-80b4-00c04fd430c8",
            version="1",
        )
        assert "__slots__" in dir(n) or not hasattr(n, "__dict__")
        with pytest.raises(dataclasses.FrozenInstanceError):
            n.version = "4"  # type: ignore[misc]
        assert hash(n) == hash(
            UUIDNotation(
                compact="6ba7b8109dad11d180b400c04fd430c8",
                hyphenated="6ba7b810-9dad-11d1-80b4-00c04fd430c8",
                urn="urn:uuid:6ba7b810-9dad-11d1-80b4-00c04fd430c8",
                version="1",
            )
        )
