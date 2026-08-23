"""Property-based tests for Language canonicalization (hypothesis)."""

from __future__ import annotations

import pytest
from hypothesis import given
from hypothesis import strategies as st

import paxman
from paxman.capabilities.Language.capability import LanguageCapability
from paxman.core.discovery import register_capability, reset_registry
from paxman.core.domain import Resolution

pytestmark = [pytest.mark.property]

_VALID_LANGUAGES = st.sampled_from(["en", "de", "fr", "zh", "ja", "es", "ar"])


@given(lang=_VALID_LANGUAGES)
def test_bare_code_round_trip(lang: str) -> None:
    reset_registry()
    try:
        register_capability(LanguageCapability())
        r = paxman.canonicalize(lang, LanguageCapability.create_contract())
        assert r.status == Resolution.SUCCESS and r.canonicalized_value == lang
        r2 = paxman.canonicalize(lang.upper(), LanguageCapability.create_contract())
        assert r2.canonicalized_value == lang  # case fold
    finally:
        reset_registry()


@given(lang=_VALID_LANGUAGES)
def test_bcp47_region_round_trip(lang: str) -> None:
    tag = f"{lang}-US"
    reset_registry()
    try:
        register_capability(LanguageCapability())
        r = paxman.canonicalize(tag, LanguageCapability.create_contract())
        assert r.status in (Resolution.SUCCESS, Resolution.INVALID)
    finally:
        reset_registry()


@given(st.sampled_from(["sl-nedis", "en-GB-oxendict", "zh-cmn", "zh-Hans-CN"]))
def test_variant_extlang_prefix_valid(tag: str) -> None:
    reset_registry()
    try:
        register_capability(LanguageCapability())
        r = paxman.canonicalize(tag, LanguageCapability.create_contract())
        assert r.status == Resolution.SUCCESS
    finally:
        reset_registry()
