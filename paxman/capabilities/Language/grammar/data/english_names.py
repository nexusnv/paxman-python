"""English language name recognition keys — single source from rules/data."""

from __future__ import annotations

from paxman.capabilities.Language.rules.data.english_language_map import (
    NAME_TO_CANONICAL,
)

ENGLISH_LANGUAGE_KEYS: frozenset[str] = frozenset(NAME_TO_CANONICAL.keys())
