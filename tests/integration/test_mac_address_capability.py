from __future__ import annotations

import pytest

import paxman
from paxman.capabilities import MacAddress
from paxman.core.discovery import register_capability, reset_registry
from paxman.core.domain import Resolution
from paxman.core.errors import MultipleMentionsError

pytestmark = [pytest.mark.integration]


@pytest.fixture(autouse=True)
def _clean_registry():
    reset_registry()
    yield
    reset_registry()


def _contract(**kwargs):
    return MacAddress.create_contract(**kwargs)


def _register():
    register_capability(MacAddress())


class TestMacAddressPipeline:
    def test_success_colon(self):
        _register()
        result = paxman.canonicalize("00:1a:2b:3c:4d:5e", _contract())
        assert result.status == Resolution.SUCCESS
        assert result.canonicalized_value == "00:1A:2B:3C:4D:5E"
        assert result.candidates[0].recognition_rule == "mac_address_recognition"

    @pytest.mark.parametrize(
        ("raw", "canonical"),
        [
            ("00-1A-2B-3C-4D-5E", "00:1A:2B:3C:4D:5E"),
            ("001A.2B3C.4D5E", "00:1A:2B:3C:4D:5E"),
            ("001A2B3C4D5E", "00:1A:2B:3C:4D:5E"),
            ("MAC: 00:1A:2B:3C:4D:5E", "00:1A:2B:3C:4D:5E"),
            ("00:1A:2B:3C:4D:5E:66:77", "00:1A:2B:3C:4D:5E:66:77"),
            ("84:71:27:ff:fe:93:17:24", "84:71:27:FF:FE:93:17:24"),
            ("48-2C-6A-1E-59-3D", "48:2C:6A:1E:59:3D"),
            ("FF:FF:FF:FF:FF:FF", "FF:FF:FF:FF:FF:FF"),
            ("00-00-5E-00-53-01", "00:00:5E:00:53:01"),
        ],
    )
    def test_success_spellings(self, raw, canonical):
        _register()
        result = paxman.canonicalize(raw, _contract())
        assert result.status == Resolution.SUCCESS
        assert result.canonicalized_value == canonical

    def test_spelling_variants_dedup_to_success(self):
        _register()
        result = paxman.canonicalize(
            "00:1A:2B:3C:4D:5E and 00-1A-2B-3C-4D-5E", _contract()
        )
        assert result.status == Resolution.SUCCESS

    def test_missing(self):
        _register()
        result = paxman.canonicalize("no hardware addresses here", _contract())
        assert result.status == Resolution.MISSING

    @pytest.mark.parametrize(
        "raw",
        [
            "00:1A:2B:3C:4D:5E:66",
            "00:1A-2B:3C-4D:5E",
            "001A2B3C4D5E6",
        ],
    )
    def test_missing_truncated_and_malformed(self, raw):
        _register()
        assert paxman.canonicalize(raw, _contract()).status == Resolution.MISSING

    def test_two_distinct_multiple_mentions(self):
        _register()
        with pytest.raises(MultipleMentionsError):
            paxman.canonicalize(
                "from 00:1A:2B:3C:4D:5E to 00-1B-77-49-54-FD", _contract()
            )

    def test_year_temporal_filter(self):
        _register()
        result = paxman.canonicalize("00:1A:2B:3C:4D:5E", _contract(year=2014))
        assert result.status == Resolution.INVALID

    def test_version_stamp_and_determinism(self):
        _register()
        a = paxman.canonicalize("001a.2b3c.4d5e", _contract())
        b = paxman.canonicalize("001a.2b3c.4d5e", _contract())
        assert a.canonicalized_value == b.canonicalized_value
        assert a.version_stamp == b.version_stamp

    def test_output_format_seam(self):
        _register()
        assert (
            paxman.canonicalize(
                "00:1A:2B:3C:4D:5E", _contract(output_format="hyphen")
            ).canonicalized_value
            == "00-1A-2B-3C-4D-5E"
        )
        assert (
            paxman.canonicalize(
                "00:1A:2B:3C:4D:5E", _contract(output_format="cisco")
            ).canonicalized_value
            == "001A.2B3C.4D5E"
        )
        assert (
            paxman.canonicalize(
                "00:1A:2B:3C:4D:5E", _contract(output_format="eui64")
            ).canonicalized_value
            == "00:1A:2B:FF:FE:3C:4D:5E"
        )
