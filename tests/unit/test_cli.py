"""Unit tests for CLI _create_contract dispatch."""

from __future__ import annotations

import pytest


@pytest.mark.unit
def test_cli_creates_orcid_contract() -> None:
    from paxman.cli import _create_contract

    contract = _create_contract("orcid")
    assert contract.capability_name == "orcid"
    assert contract.output_format == "orcid"
