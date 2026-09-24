"""Tests for Domain generated data modules (Task 3)."""

import json
from pathlib import Path

import pytest

from paxman.capabilities.Domain.grammar.data import idna_mapping
from paxman.capabilities.Domain.rules.data import root_zone_tlds
from paxman.capabilities.URL.rules.data import idna_uts46_mapping as url_table

pytestmark = pytest.mark.capability


class TestIdnaMapping:
    """UTS #46 table pin: shipped table 15.1.0, shared with URL."""

    def test_idna_version_is_15_1_0(self) -> None:
        assert idna_mapping.IDNA_VERSION == "15.1.0"

    def test_idna_version_matches_url_shipped_table(self) -> None:
        assert idna_mapping.IDNA_VERSION == url_table.IDNA_VERSION

    def test_mapping_shape(self) -> None:
        assert idna_mapping.MAPPING[0x0041] == "0061"
        assert idna_mapping.MAPPING[0x3002] == "002E"
        assert idna_mapping.MAPPING[0xFF45] == "0065"
        assert idna_mapping.MAPPING[0xFB00] == "0066 0066"
        assert all(isinstance(cp, int) for cp in idna_mapping.MAPPING)
        assert all(
            value.isascii()
            and all(
                1 <= len(part) <= 6 and all(c in "0123456789ABCDEFabcdef" for c in part)
                for part in value.split(" ")
            )
            for value in idna_mapping.MAPPING.values()
        )

    def test_statuses_shape(self) -> None:
        assert idna_mapping.STATUSES["005B..0060"] == "disallowed_STD3_valid"
        assert idna_mapping.STATUSES["200C..200D"] == "deviation"
        assert all(key.replace("..", "").isalnum() for key in idna_mapping.STATUSES)


class TestRootZoneTlds:
    """IANA root-zone snapshot pin: tlds-alpha v2026092300, 1,438 entries."""

    def test_root_zone_entry_count(self) -> None:
        assert len(root_zone_tlds.ROOT_ZONE_TLDS) == 1438

    def test_root_zone_members(self) -> None:
        assert {"com", "org", "net", "de", "jp", "xn--p1ai"} <= (
            root_zone_tlds.ROOT_ZONE_TLDS
        )

    def test_root_zone_non_members(self) -> None:
        assert {"xn--mnchen-3ya", "123", "1"}.isdisjoint(root_zone_tlds.ROOT_ZONE_TLDS)

    def test_root_zone_all_lowercase(self) -> None:
        assert all(t == t.lower() for t in root_zone_tlds.ROOT_ZONE_TLDS)

    def test_snapshot_version(self) -> None:
        assert root_zone_tlds.SNAPSHOT_VERSION == "tlds-alpha-by-domain.txt@2026092300"

    def test_root_zone_snapshot_consistency(self) -> None:
        snapshot_path = (
            Path(__file__).resolve().parents[3]
            / "paxman"
            / "shared_data"
            / "root_zone_snapshot.json"
        )
        snapshot = json.loads(snapshot_path.read_text(encoding="utf-8"))
        assert snapshot["_meta"]["version"] == "2026092300"
        assert snapshot["_meta"]["entry_count"] == 1438
        assert snapshot["_meta"]["source"].endswith("tlds-alpha-by-domain.txt")
        assert {t.lower() for t in snapshot["tlds"]} == set(
            root_zone_tlds.ROOT_ZONE_TLDS
        )
