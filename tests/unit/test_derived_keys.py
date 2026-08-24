"""Derived recognition keys — single source of truth (F8, D10)."""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.unit


def test_bic_country_codes_derived() -> None:
    from paxman.capabilities.BIC.grammar.data.country_codes import (
        COUNTRY_CODES as GRAMMAR_CODES,
    )
    from paxman.capabilities.BIC.rules.iso_9362_ed2022 import (
        COUNTRY_CODES as RULE_CODES,
    )

    assert GRAMMAR_CODES == RULE_CODES


def test_language_name_keys_derived() -> None:
    from paxman.capabilities.Language.grammar.data.names import NAME_TOKENS

    assert len(NAME_TOKENS) > 77
    assert "united states" not in NAME_TOKENS
