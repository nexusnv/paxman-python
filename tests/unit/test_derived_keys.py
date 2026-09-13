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
    from paxman.capabilities.Language.grammar.data.english_names import (
        ENGLISH_LANGUAGE_KEYS,
    )
    from paxman.capabilities.Language.grammar.data.localized_names import (
        LOCALIZED_LANGUAGE_KEYS,
    )
    from paxman.capabilities.Language.rules.data.english_language_map import (
        LOCALIZED_NAME_TO_CANONICAL,
        NAME_TO_CANONICAL,
    )

    assert frozenset(NAME_TO_CANONICAL) == ENGLISH_LANGUAGE_KEYS
    assert frozenset(LOCALIZED_NAME_TO_CANONICAL) == LOCALIZED_LANGUAGE_KEYS
    assert "united states" not in (ENGLISH_LANGUAGE_KEYS | LOCALIZED_LANGUAGE_KEYS)


def test_language_grammar_data_has_no_synthetic_keys() -> None:
    from pathlib import Path

    data_dir = Path("paxman/capabilities/Language/grammar/data")
    leaked = sorted(
        path.name
        for path in data_dir.glob("*.py")
        if "synthetic" in path.read_text(encoding="utf-8").lower()
    )
    assert not leaked, f"synthetic keys in shipped grammar data: {leaked}"
