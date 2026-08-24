"""Freeze compilation + recognition_revision."""

from paxman.capabilities.Country.capability import CountryCapability
from paxman.core.discovery import (
    freeze_registry,
    is_registry_frozen,
    register_capability,
    reset_registry,
)
from paxman.core.domain import VersionStamp


def test_version_stamp_has_recognition_revision() -> None:
    vs = VersionStamp(paxman_version="0.1.0", recognition_revision="abc123")
    assert vs.recognition_revision == "abc123"
    assert vs.paxman_version == "0.1.0"


def test_freeze_computes_recognition_revision() -> None:
    reset_registry()
    register_capability(CountryCapability())
    freeze_registry()
    assert is_registry_frozen() is True
    from paxman.core.discovery import get_recognition_revision

    rev = get_recognition_revision()
    assert isinstance(rev, str) and len(rev) > 0
    reset_registry()
    # default after reset should be "0"
    from paxman.core.discovery import get_recognition_revision as gr2

    assert gr2() == "0"
