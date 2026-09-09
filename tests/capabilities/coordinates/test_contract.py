"""Tests for CoordinatesContract."""

import dataclasses
import inspect
from inspect import Parameter

import pytest

from paxman.capabilities.Coordinates.contract import (
    CoordinatesContract,
    create_contract,
)
from paxman.core.errors import ContractError

pytestmark = [pytest.mark.capability]


def test_default_output_format_decimal() -> None:
    c = CoordinatesContract()
    assert c.capability_name == "coordinates"
    assert c.output_format == "decimal"
    assert CoordinatesContract.DEFAULT_OUTPUT_FORMAT == "decimal"


def test_offered_excludes_default() -> None:
    assert "decimal" not in CoordinatesContract.OFFERED_OUTPUT_FORMATS
    assert (
        frozenset({"iso6709", "geo_uri", "geojson_pair", "dms", "dm"})
        == CoordinatesContract.OFFERED_OUTPUT_FORMATS
    )


def test_resolve_output_format_iso6709() -> None:
    c = CoordinatesContract(output_format="iso6709")
    assert c.output_format == "iso6709"
    c2 = create_contract(output_format="iso6709")
    assert c2.output_format == "iso6709"


@pytest.mark.parametrize(
    "fmt",
    ["geo_uri", "geojson_pair", "dms", "dm", "iso6709"],
)
def test_offered_formats_resolve(fmt: str) -> None:
    assert CoordinatesContract(output_format=fmt).output_format == fmt
    assert create_contract(output_format=fmt).output_format == fmt


@pytest.mark.parametrize("fmt", [None, "default", "decimal"])
def test_default_variants_resolve_to_decimal(fmt: str | None) -> None:
    assert CoordinatesContract(output_format=fmt).output_format == "decimal"
    assert create_contract(output_format=fmt).output_format == "decimal"


def test_rejects_unknown_format() -> None:
    with pytest.raises(ContractError):
        CoordinatesContract(output_format="utm")
    with pytest.raises(ContractError):
        create_contract(output_format="utm")
    with pytest.raises(ContractError):
        CoordinatesContract(output_format="unknown_format")


def test_capability_name_frozen() -> None:
    c = CoordinatesContract()
    assert c.capability_name == "coordinates"
    with pytest.raises(dataclasses.FrozenInstanceError):
        c.capability_name = "other"  # type: ignore[misc]
    with pytest.raises(dataclasses.FrozenInstanceError):
        c.output_format = "iso6709"  # type: ignore[misc]


def test_create_contract_keyword_only() -> None:
    with pytest.raises(TypeError):
        create_contract("iso6709")  # type: ignore[misc]
    # also ensure capability's factory is keyword-only (homogeneity)
    from paxman.capabilities.Coordinates.capability import CoordinatesCapability

    sig = inspect.signature(CoordinatesCapability.create_contract)
    params = list(sig.parameters.values())
    assert all(p.kind == Parameter.KEYWORD_ONLY for p in params)
    with pytest.raises(TypeError):
        CoordinatesCapability.create_contract("iso6709")  # type: ignore[misc]


def test_create_contract_common_block_passthrough() -> None:
    c = create_contract(
        excluded_rules=["Section 6-coordinate-structure"],
        pinned_rules=["Section 6-coordinate-structure"],
        year=2022,
        output_format="dms",
        extra_grammars=["extra"],
        suppress_common_words=True,
    )
    assert c.excluded_rules == ("Section 6-coordinate-structure",)
    assert c.pinned_rules == ("Section 6-coordinate-structure",)
    assert c.year == 2022
    assert c.output_format == "dms"
    assert c.extra_grammars == ("extra",)
    assert c.suppress_common_words is True


def test_extra_grammars_defaults_to_empty() -> None:
    assert CoordinatesContract().extra_grammars == ()
    assert create_contract().extra_grammars == ()


def test_is_frozen() -> None:
    c = CoordinatesContract()
    with pytest.raises(dataclasses.FrozenInstanceError):
        c.year = 2022  # type: ignore[misc]
