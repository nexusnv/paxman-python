"""Tests for LEI rules — both publications (ISO PARSER + GLEIF LOOKUP).

TDD per plan Tasks 4-5.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from paxman.capabilities.LEI.contract import LEIContract
from paxman.capabilities.LEI.notation import LEINotation
from paxman.capabilities.LEI.rules.gleif_lou_prefix_list_ed2026 import (
    PUBLICATION as GLEIF_PUBLICATION,
)
from paxman.capabilities.LEI.rules.gleif_lou_prefix_list_ed2026 import (
    Section1LOUPrefixMembership,
)
from paxman.capabilities.LEI.rules.iso_17442_1_ed2020 import (
    PUBLICATION as ISO_PUBLICATION,
)
from paxman.capabilities.LEI.rules.iso_17442_1_ed2020 import (
    Section4LEIStructureMOD9710,
)
from paxman.core.domain import RuleStrategy

pytestmark = [pytest.mark.capability]

CONTRACT = LEIContract()

# Checksum-verified vectors (whole-string MOD 97-10 remainder == 1).
VALID = [
    "213800KUD8LAJWSQ9D15",
    "5493000IBP32UQZ0KL24",
    "213800WSGIIZCXF1P572",
    "506700GE1G29325QX363",
    "7LTWFZYICNSX8D621K86",  # positions 5-6 carry "FZ", not "00"
]
GENERATION = "213800D1L3R2MWV39G88"  # check digits "88" for first18 ...V39G
BAD_CHECKSUM = "213800KUD8LXJWSQ9D15"  # remainder 55
# Fabricated prefix, check digits computed so whole-string mod97 == 1:
# structure+checksum valid, but "ZZZZ" is not an accredited LOU prefix.
FABRICATED = "ZZZZ0000000000000016"


def _notation(compact: str) -> LEINotation:
    return LEINotation(
        lou_prefix=compact[0:4],
        entity_block=compact[4:18],
        check_digits=compact[18:20],
        compact=compact,
    )


def test_parser_valid() -> None:
    rule = Section4LEIStructureMOD9710()
    for v in VALID:
        assert rule.matches(_notation(v), CONTRACT) is True, v


def test_parser_non00_accepted() -> None:
    rule = Section4LEIStructureMOD9710()
    n = _notation("7LTWFZYICNSX8D621K86")
    assert n.entity_block.startswith("FZ")
    assert rule.matches(n, CONTRACT) is True


def test_parser_bad_checksum() -> None:
    rule = Section4LEIStructureMOD9710()
    assert rule.matches(_notation(BAD_CHECKSUM), CONTRACT) is False


def test_parser_generation_vector() -> None:
    rule = Section4LEIStructureMOD9710()
    assert rule.matches(_notation(GENERATION), CONTRACT) is True


def test_parser_digit_only_lei_accepted() -> None:
    # Review finding 1: digit-only LEIs carry no cased characters, so
    # str.isupper() is False even though [A-Z0-9] permits them.
    from paxman.capabilities.LEI.rules.iso_17442_1_ed2020 import (
        _mod97_10_valid as _parser_mod97,
    )

    compact = "1128" + "0" * 14 + "02"
    assert _parser_mod97(compact) is True
    assert Section4LEIStructureMOD9710().matches(_notation(compact), CONTRACT) is True


def test_lookup_valid_prefixes() -> None:
    rule = Section1LOUPrefixMembership()
    for v in VALID:
        assert rule.matches(_notation(v), CONTRACT) is True, v


def test_lookup_rejects_unknown_prefix() -> None:
    rule = Section1LOUPrefixMembership()
    # Structure + checksum are valid; only the prefix is unattested.
    assert Section4LEIStructureMOD9710().matches(_notation(FABRICATED), CONTRACT)
    assert rule.matches(_notation(FABRICATED), CONTRACT) is False


def test_lookup_rejects_bad_checksum_valid_prefix() -> None:
    rule = Section1LOUPrefixMembership()
    assert rule.matches(_notation(BAD_CHECKSUM), CONTRACT) is False


def test_lookup_digit_only_lei_accepted() -> None:
    # Review finding 1: digit-only LEIs carry no cased characters, so
    # str.isupper() is False even though [A-Z0-9] permits them.
    from paxman.capabilities.LEI.rules.gleif_lou_prefix_list_ed2026 import (
        _mod97_10_valid as _lookup_mod97,
    )

    compact = "1128" + "0" * 14 + "02"
    assert _lookup_mod97(compact) is True
    assert Section1LOUPrefixMembership().matches(_notation(compact), CONTRACT) is True


def test_normalize_agreement() -> None:
    parser = Section4LEIStructureMOD9710()
    lookup = Section1LOUPrefixMembership()
    for v in VALID:
        n = _notation(v)
        assert parser.normalize(n, CONTRACT) == v
        assert lookup.normalize(n, CONTRACT) == v
        assert parser.normalize(n, CONTRACT) == lookup.normalize(n, CONTRACT)


def test_provenance_attrs() -> None:
    assert ISO_PUBLICATION.authority == "ISO"
    assert ISO_PUBLICATION.specification_name == "ISO 17442-1:2020"
    assert ISO_PUBLICATION.reference_url == "https://www.iso.org/standard/78829.html"
    assert ISO_PUBLICATION.version == "2020"
    assert ISO_PUBLICATION.kind == "specification"
    assert ISO_PUBLICATION.lifecycle == "active"
    assert ISO_PUBLICATION.publication_year == 2020

    assert GLEIF_PUBLICATION.authority == "GLEIF"
    assert GLEIF_PUBLICATION.specification_name == "GLEIF LOU prefix list"
    assert GLEIF_PUBLICATION.reference_url == (
        "https://www.gleif.org/en/lei-data/gleif-concatenated-file/"
        "download-the-concatenated-file"
    )
    assert GLEIF_PUBLICATION.version == "Rolling"
    assert GLEIF_PUBLICATION.kind == "registry"
    assert GLEIF_PUBLICATION.lifecycle == "active"
    assert GLEIF_PUBLICATION.publication_year == 2026


def test_strategy_six_attrs() -> None:
    parser = Section4LEIStructureMOD9710()
    lookup = Section1LOUPrefixMembership()

    assert parser.name == "Section 4-lei-structure-mod97-10"
    assert parser.strategy is RuleStrategy.PARSER
    assert parser.provenance is ISO_PUBLICATION
    assert isinstance(parser.citation, str) and parser.citation
    assert parser.target_semantics == frozenset({"lei_recognition"})
    assert parser.requires_features == frozenset()

    assert lookup.name == "Section 1-lou-prefix-membership"
    assert lookup.strategy is RuleStrategy.LOOKUP_TABLE
    assert lookup.provenance is GLEIF_PUBLICATION
    assert isinstance(lookup.citation, str) and lookup.citation
    assert lookup.target_semantics == frozenset({"lei_recognition"})
    assert lookup.requires_features == frozenset()


def test_no_output_format_token() -> None:
    rules_dir = Path("paxman/capabilities/LEI/rules")
    for path in rules_dir.rglob("*.py"):
        source = path.read_text(encoding="utf-8")
        assert re.search(r"output_format", source) is None, path


def test_prefix_set_present() -> None:
    from paxman.capabilities.LEI.rules.data import lou_prefixes

    assert {"2138", "5493", "5067", "7LTW"} <= lou_prefixes.ACCREDITED_LOU_PREFIXES
    header = lou_prefixes.__doc__ or ""
    assert "append-only" in header.lower()
    assert "never delete" in header.lower() or "never removed" in header.lower()
    assert "census" in header.lower()
