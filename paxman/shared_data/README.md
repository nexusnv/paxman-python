# Shared Vocabulary Snapshots

## Currency / Money

Source of truth for CLDR currency data and ISO 4217 list-one.

- Authority: Unicode CLDR v47 (en + es) and ISO 4217 (2015 list-one snapshot).
- Canonical file: `currency_snapshot.json` (JSON, UTF-8, sorted keys).
- Generated outputs: `paxman/capabilities/Currency/{grammar,rules}/data/*` and `paxman/capabilities/Money/{grammar,rules}/data/*` via `tools/regenerate_currency_data.py`.
- Edit workflow: update snapshot JSON (with citation), then `uv run python tools/regenerate_currency_data.py` and `--check` in CI.

## Language

Source of truth for IANA grandfathered tags, Preferred-Value map, and English/localized display-name keys.

- Authority: IANA Language Subtag Registry File-Date 2026-08-08 + ISO 639 family + BCP47 RFC 5646.
- Canonical file: `language_snapshot.json` (JSON, UTF-8, sorted keys).
- Generated outputs: `paxman/capabilities/Language/grammar/data/grandfathered_tags.py`, `paxman/capabilities/Language/grammar/data/english_names.py`, `paxman/capabilities/Language/grammar/data/localized_names.py`, `paxman/capabilities/Language/rules/data/iana_grandfathered.py`, `paxman/capabilities/Language/rules/data/english_language_map.py` via `tools/regenerate_language_data.py`.
- Edit workflow: update snapshot JSON (with citation), then `uv run python tools/regenerate_language_data.py` and `--check` in CI.

Mandate M8: Sibling imports remain banned. Shared vocabularies regenerate into per-capability tables, never imported across capabilities. Grammar/Grammar Data must not import from rules/rules data.
