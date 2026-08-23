"""Localized (CLDR) language name recognition keys — single source from rules/data."""

from __future__ import annotations

from paxman.capabilities.Language.rules.data.english_language_map import (
    LOCALIZED_NAME_TO_CANONICAL,
)

LOCALIZED_LANGUAGE_KEYS: frozenset[str] = frozenset(LOCALIZED_NAME_TO_CANONICAL.keys())
