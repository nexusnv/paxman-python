from dataclasses import FrozenInstanceError

import pytest

from paxman.capabilities.Language.contract import LanguageContract
from paxman.core.errors import ContractError

pytestmark = [pytest.mark.capability]


def test_defaults():
    c = LanguageContract()
    assert c.output_format == "bcp47"
    assert c.capability_name == "language"
    assert LanguageContract.DEFAULT_OUTPUT_FORMAT == "bcp47"
    assert (
        frozenset({"alpha2", "alpha3", "alpha3-bib", "name"})
        == LanguageContract.OFFERED_OUTPUT_FORMATS
    )
    assert c.include_localized is False
    assert c.include_collective is False
    assert c.include_private is False
    assert c.include_grandfathered is True


def test_offered():
    for fmt in ("alpha2", "alpha3", "alpha3-bib", "name"):
        assert LanguageContract(output_format=fmt).output_format == fmt


def test_default_alias():
    for alias in (None, "default", "bcp47"):
        assert LanguageContract(output_format=alias).output_format == "bcp47"


def test_invalid_raises():
    for bad in ("paper", "iso", "hyphenated", "", "BCP47"):
        with pytest.raises(ContractError):
            LanguageContract(output_format=bad)  # type: ignore[arg-type]


def test_flags():
    c = LanguageContract(include_private=True, include_collective=True)
    assert c.include_private is True and c.include_collective is True


def test_frozen():
    c = LanguageContract()
    with pytest.raises(FrozenInstanceError):
        c.output_format = "alpha2"  # type: ignore[misc]
