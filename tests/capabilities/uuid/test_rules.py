"""Tests for Section4UUIDFormat (RFC 9562 §4 structure, PARSER)."""

import pytest

from paxman.capabilities.UUID.contract import UUIDContract
from paxman.capabilities.UUID.grammar.uuid_recognition import UUIDRecognitionGrammar
from paxman.capabilities.UUID.notation import UUIDNotation
from paxman.capabilities.UUID.rules.rfc_9562_ed2024 import (
    PUBLICATION,
    Section4UUIDFormat,
)
from paxman.core.domain import RuleStrategy


def _notation(compact: str) -> UUIDNotation:
    hyphenated = (
        f"{compact[:8]}-{compact[8:12]}-{compact[12:16]}"
        f"-{compact[16:20]}-{compact[20:]}"
    )
    return UUIDNotation(
        compact=compact,
        hyphenated=hyphenated,
        urn=f"urn:uuid:{hyphenated}",
        version=compact[12] if len(compact) == 32 else "?",
    )


@pytest.mark.capability
class TestSection4UUIDFormat:
    """Structure-only validation; version/variant never gate."""

    def setup_method(self) -> None:
        self.rule = Section4UUIDFormat()
        self.contract = UUIDContract()

    def test_name_strategy_provenance(self) -> None:
        assert self.rule.name == "Section 4-uuid-format"
        assert self.rule.strategy == RuleStrategy.PARSER
        assert self.rule.target_semantics == frozenset({"uuid_recognition"})
        assert self.rule.requires_features == frozenset()
        assert PUBLICATION.authority == "IETF"
        assert PUBLICATION.specification_name == "RFC 9562"
        assert PUBLICATION.publication_year == 2024

    def test_valid_structures(self) -> None:
        grammar = UUIDRecognitionGrammar()
        for text in (
            "6ba7b810-9dad-11d1-80b4-00c04fd430c8",
            "6ba7b8109dad11d180b400c04fd430c8",
            "{6BA7B810-9DAD-11D1-80B4-00C04FD430C8}",
            "urn:uuid:6fa459ea-ee8a-3ca4-894e-db77e160355e",
            "00000000-0000-0000-0000-000000000000",
            "ffffffff-ffff-ffff-ffff-ffffffffffff",
        ):
            (match,) = grammar.recognize(text)
            assert self.rule.matches(match.notation, self.contract) is True, text

    def test_version_nibble_informative(self) -> None:
        """v0/vF structures still match — generation≠storage (RFC §2.1-6)."""
        assert (
            self.rule.matches(_notation("0" * 12 + "0" + "0" * 19), self.contract)
            is True
        )
        assert (
            self.rule.matches(_notation("0" * 12 + "f" + "0" * 19), self.contract)
            is True
        )

    def test_rejects_malformed(self) -> None:
        assert self.rule.matches(_notation("0" * 31), self.contract) is False
        bad = UUIDNotation(
            compact="6ba7b8109dad11d180b400c04fd430cg",
            hyphenated="6ba7b810-9dad-11d1-80b4-00c04fd430cg",
            urn="urn:uuid:6ba7b810-9dad-11d1-80b4-00c04fd430cg",
            version="1",
        )
        assert self.rule.matches(bad, self.contract) is False

    def test_normalize_exact_lowercase_hyphenated(self) -> None:
        n = _notation("6ba7b8109dad11d180b400c04fd430c8")
        assert (
            self.rule.normalize(n, self.contract)
            == "6ba7b810-9dad-11d1-80b4-00c04fd430c8"
        )
