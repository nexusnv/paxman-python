"""Tests for VersionStamp dataclass."""

from __future__ import annotations

import dataclasses

import pytest

from paxman.core.domain import VersionStamp


class TestVersionStamp:
    @pytest.mark.unit
    def test_immutable(self) -> None:
        vs = VersionStamp(paxman_version="0.1.0")
        with pytest.raises(AttributeError):
            vs.paxman_version = "0.2.0"

    @pytest.mark.unit
    def test_equality(self) -> None:
        a = VersionStamp(paxman_version="0.1.0")
        b = VersionStamp(paxman_version="0.1.0")
        assert a == b

    @pytest.mark.unit
    def test_inequality(self) -> None:
        a = VersionStamp(paxman_version="0.1.0")
        b = VersionStamp(paxman_version="0.2.0")
        assert a != b

    @pytest.mark.unit
    def test_hashable(self) -> None:
        vs = VersionStamp(paxman_version="0.1.0")
        assert hash(vs) is not None

    @pytest.mark.unit
    def test_surface_is_exactly_paxman_version(self) -> None:
        field_names = tuple(f.name for f in dataclasses.fields(VersionStamp))
        assert field_names == ("paxman_version", "recognition_revision")
        vs = VersionStamp(paxman_version="0.1.0")
        assert vs.recognition_revision == "0"
        assert not hasattr(vs, "replay_hash")
