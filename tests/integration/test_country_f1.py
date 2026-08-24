"""F1 regression: embedded names recognized, short codes compete honestly."""

import paxman
from paxman.capabilities.Country.capability import CountryCapability
from paxman.core.discovery import register_capability, reset_registry
from paxman.core.errors import MultipleMentionsError


def _contract():  # type: ignore[no-untyped-def]
    return CountryCapability.create_contract()


def test_ship_to_united_states_is_multiple_mentions() -> None:
    reset_registry()
    register_capability(CountryCapability())
    try:
        paxman.canonicalize("Ship to United States please", _contract())
    except MultipleMentionsError as e:
        msg = str(e)
        # Engine exposes canonical values; raw mentions are visible via
        # the two distinct values (TO via alpha2, US via name).
        assert "2 distinct mentions" in msg
        assert "TO" in msg and "US" in msg
        return
    raise AssertionError("expected MultipleMentionsError")
