"""Recognition-to-rule data consistency for Language capability.

Every language name the Language name grammar recognizes must be backed
by at least one authority rule-data mapping. If a recognition key had
no rule-data mapping, the grammar could emit a notation that no
validation rule can resolve — a pipeline dead end.

Completeness note (subset data): English and localized display names are
curatorial subsets (60 + 24 entries) generated from
paxman/shared_data/language_snapshot.json — not the full IANA
Description set (7,900+) or CLDR v46 root locale. Names outside the
subset are MISSING (grammar emits no match) rather than INVALID,
avoiding false negatives under the current completeness contract.
Full IANA Description coverage is tracked as follow-up work; until then
unsupported provenance is documented in the snapshot _meta and
generated file headers.

Grammar data must not import from rules — separation is enforced by
this test importing only generated grammar keys and generated rule maps
that share the same snapshot, and by import-linter.
"""

from __future__ import annotations

import pytest

from paxman.capabilities.Language.grammar.data.english_names import (
    ENGLISH_LANGUAGE_KEYS,
)
from paxman.capabilities.Language.grammar.data.localized_names import (
    LOCALIZED_LANGUAGE_KEYS,
)
from paxman.capabilities.Language.notation import normalize_name
from paxman.capabilities.Language.rules.data.english_language_map import (
    LOCALIZED_NAME_TO_CANONICAL,
    NAME_TO_CANONICAL,
)

pytestmark = [pytest.mark.capability]


def _normalized_keys(mapping: dict[str, str]) -> set[str]:
    return {normalize_name(k) for k in mapping}


def _uncovered_report(uncovered: list[str]) -> str:
    lines = ["Recognition keys with no backing rule-data mapping:"]
    lines.extend(f"  - {k}" for k in uncovered)
    return "\n".join(lines)


class TestRecognitionKeysAreRuleDataCovered:
    """Recognition key sets must be covered by authority rule-data maps."""

    def test_every_recognition_key_has_rule_data_mapping(self) -> None:
        recognized = ENGLISH_LANGUAGE_KEYS | LOCALIZED_LANGUAGE_KEYS
        rule_data = _normalized_keys(NAME_TO_CANONICAL) | _normalized_keys(
            LOCALIZED_NAME_TO_CANONICAL
        )
        uncovered = sorted(recognized - rule_data)
        assert not uncovered, _uncovered_report(uncovered)

    def test_every_english_key_has_rule_data(self) -> None:
        uncovered = sorted(ENGLISH_LANGUAGE_KEYS - _normalized_keys(NAME_TO_CANONICAL))
        assert not uncovered, _uncovered_report(uncovered)

    def test_every_localized_key_has_cldr_rule_data(self) -> None:
        uncovered = sorted(
            LOCALIZED_LANGUAGE_KEYS - _normalized_keys(LOCALIZED_NAME_TO_CANONICAL)
        )
        assert not uncovered, _uncovered_report(uncovered)

    def test_grammar_data_does_not_import_rules(self) -> None:
        """Grammar data modules must not import from rules."""
        import ast
        from pathlib import Path

        for rel in [
            "paxman/capabilities/Language/grammar/data/english_names.py",
            "paxman/capabilities/Language/grammar/data/localized_names.py",
            "paxman/capabilities/Language/grammar/data/grandfathered_tags.py",
        ]:
            src = Path(rel).read_text(encoding="utf-8")
            tree = ast.parse(src)
            imports = [
                n for n in ast.walk(tree) if isinstance(n, (ast.Import, ast.ImportFrom))
            ]
            for node in imports:
                if isinstance(node, ast.ImportFrom) and node.module:
                    assert "paxman.capabilities.Language.rules" not in node.module, (
                        f"{rel} imports from rules: {node.module}"
                    )
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        assert "paxman.capabilities.Language.rules" not in alias.name, (
                            f"{rel} imports rules: {alias.name}"
                        )
