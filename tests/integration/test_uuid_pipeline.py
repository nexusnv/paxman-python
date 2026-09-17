"""Integration tests for the UUID capability through the full pipeline.

Research vectors: RFC 9562 Fig 1 + Python stdlib uuid3/uuid5-DNS examples.
Cross-capability notes: bare-32 LLDD runs also match the IBAN shape —
each side resolves under its own contract (UUID SUCCESS, IBAN INVALID
unless MOD97 passes); URN-form input is URI-shaped but resolves under
the UUID contract here (URL-side behavior belongs to URL tests).
"""

from __future__ import annotations

from collections.abc import Iterator

import pytest

import paxman
from paxman.capabilities.IBAN.capability import IBANCapability
from paxman.capabilities.UUID.capability import UUIDCapability
from paxman.core.discovery import reset_registry
from paxman.core.domain import Resolution
from paxman.core.errors import ContractError, MultipleMentionsError

_CANON = "6ba7b810-9dad-11d1-80b4-00c04fd430c8"


@pytest.fixture(autouse=True)
def _clean_registry() -> Iterator[None]:
    """Reset the capability registry before and after each test."""
    reset_registry()
    yield
    reset_registry()


@pytest.mark.integration
class TestUUIDPipelineSuccess:
    """Carriers collapse to one lowercase hyphenated canonical."""

    @pytest.mark.parametrize(
        ("text", "expected_value", "expected_span"),
        [
            ("6ba7b810-9dad-11d1-80b4-00c04fd430c8", _CANON, (0, 36)),
            ("6BA7B810-9DAD-11D1-80B4-00C04FD430C8", _CANON, (0, 36)),
            ("6ba7b8109dad11d180b400c04fd430c8", _CANON, (0, 32)),
            ("{6ba7b810-9dad-11d1-80b4-00c04fd430c8}", _CANON, (0, 38)),
            ("urn:uuid:6ba7b810-9dad-11d1-80b4-00c04fd430c8", _CANON, (0, 45)),
            (
                "f81d4fae-7dec-11d0-a765-00a0c91e6bf6",
                "f81d4fae-7dec-11d0-a765-00a0c91e6bf6",
                (0, 36),
            ),
            (
                "6fa459ea-ee8a-3ca4-894e-db77e160355e",
                "6fa459ea-ee8a-3ca4-894e-db77e160355e",
                (0, 36),
            ),
            (
                "886313e1-3b8a-5372-9b90-0c9aee199e5d",
                "886313e1-3b8a-5372-9b90-0c9aee199e5d",
                (0, 36),
            ),
            (
                "00000000-0000-0000-0000-000000000000",
                "00000000-0000-0000-0000-000000000000",
                (0, 36),
            ),
            (
                "ffffffff-ffff-ffff-ffff-ffffffffffff",
                "ffffffff-ffff-ffff-ffff-ffffffffffff",
                (0, 36),
            ),
        ],
    )
    def test_success_rows(
        self, text: str, expected_value: str, expected_span: tuple[int, int]
    ) -> None:
        """Research vectors canonicalize (RFC Fig 1, stdlib uuid3/uuid5, Nil/Max)."""
        paxman.register_all_shipped()
        contract = UUIDCapability.create_contract()
        result = paxman.canonicalize(text, contract)

        assert result.status == Resolution.SUCCESS
        assert result.canonicalized_value == expected_value
        assert result.span == expected_span
        assert {c.value for c in result.candidates} == {expected_value}
        for candidate in result.candidates:
            assert candidate.validation_rule == "Section 4-uuid-format"
            assert candidate.provenance[0].authority == "IETF"

    def test_embedded_span(self) -> None:
        paxman.register_all_shipped()
        contract = UUIDCapability.create_contract()
        result = paxman.canonicalize(f"request {_CANON} done", contract)

        assert result.status == Resolution.SUCCESS
        assert result.canonicalized_value == _CANON
        assert result.span == (8, 44)


@pytest.mark.integration
class TestUUIDPipelineMissing:
    """Bad length/charset/prose claims nothing."""

    @pytest.mark.parametrize(
        "text",
        [
            "6ba7b8109dad11d180b400c04fd430c",  # 31-hex
            "6ba7b8109dad11d180b400c04fd430c8a",  # 33-hex
            "6ba7b810-9dad-11d1-80b4-00c04fd430c",  # short group
            "6ga7b810-9dad-11d1-80b4-00c04fd430c8",  # non-hex
            "hello world",
            "1234567812345678123456781234567",  # 31 digits, no letters
        ],
    )
    def test_missing_rows(self, text: str) -> None:
        paxman.register_all_shipped()
        contract = UUIDCapability.create_contract()
        result = paxman.canonicalize(text, contract)

        assert result.status == Resolution.MISSING


@pytest.mark.integration
class TestUUIDPipelineAmbiguity:
    """Two distinct ids fail fast under single_value."""

    def test_two_distinct_raise(self) -> None:
        paxman.register_all_shipped()
        contract = UUIDCapability.create_contract()
        with pytest.raises(MultipleMentionsError):
            paxman.canonicalize(
                "6ba7b810-9dad-11d1-80b4-00c04fd430c8 then "
                "6fa459ea-ee8a-3ca4-894e-db77e160355e",
                contract,
            )


@pytest.mark.integration
class TestUUIDSiblingOverlap:
    """LLDD-32 resolves per-capability: UUID SUCCESS, IBAN INVALID."""

    def test_iban_shaped_bare_hex(self) -> None:
        text = "ab127815091827364554637281901234"
        assert len(text) == 32
        paxman.register_all_shipped()

        uuid_result = paxman.canonicalize(text, UUIDCapability.create_contract())
        assert uuid_result.status == Resolution.SUCCESS

        iban_result = paxman.canonicalize(text, IBANCapability.create_contract())
        assert iban_result.status == Resolution.INVALID


@pytest.mark.integration
class TestUUIDPipelineContract:
    """Temporal filtering and format policy."""

    def test_year_filter_invalid(self) -> None:
        paxman.register_all_shipped()
        contract = UUIDCapability.create_contract(year=2020)
        result = paxman.canonicalize(_CANON, contract)

        assert result.status == Resolution.INVALID

    def test_unoffered_format_contract_error(self) -> None:
        with pytest.raises(ContractError):
            UUIDCapability.create_contract(output_format="upper")

    def test_determinism_spot_check(self) -> None:
        paxman.register_all_shipped()
        contract = UUIDCapability.create_contract()
        first = paxman.canonicalize("{6BA7B810-9DAD-11D1-80B4-00C04FD430C8}", contract)
        second = paxman.canonicalize("{6BA7B810-9DAD-11D1-80B4-00C04FD430C8}", contract)

        assert first.status == Resolution.SUCCESS
        assert first.canonicalized_value == second.canonicalized_value == _CANON
