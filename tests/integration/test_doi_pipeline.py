"""Integration tests for the DOI capability through the full pipeline.

Research vectors: ISO 26324:2025 via DOI Handbook Ch.3 (namespace/case),
Ch.5 (proxy/shortDOI), Crossref display guidelines, Wikidata P356.
Cross-capability notes: resolver-URL input also matches the URL shape —
each side resolves under its own contract (DOI SUCCESS bare, URL SUCCESS
absolute URI); bare numerics stay clear of Phone/Date grammars.
"""

from __future__ import annotations

from collections.abc import Iterator

import pytest

import paxman
from paxman.capabilities.Date.capability import DateCapability
from paxman.capabilities.DOI.capability import DOICapability
from paxman.capabilities.Phone.capability import PhoneCapability
from paxman.capabilities.URL.capability import URLCapability
from paxman.core.discovery import reset_registry
from paxman.core.domain import Resolution
from paxman.core.errors import ContractError, MultipleMentionsError


@pytest.fixture(autouse=True)
def _clean_registry() -> Iterator[None]:
    """Reset the capability registry before and after each test."""
    reset_registry()
    yield
    reset_registry()


@pytest.mark.integration
class TestDOIPipelineSuccess:
    """Carriers collapse to one ASCII-folded bare canonical."""

    @pytest.mark.parametrize(
        ("text", "expected_value", "expected_span"),
        [
            ("10.1038/nature12345", "10.1038/nature12345", (0, 19)),
            ("10.1038/NATURE12345", "10.1038/nature12345", (0, 19)),
            ("10.1000/182", "10.1000/182", (0, 11)),
            ("10.13003/5jchdy", "10.13003/5jchdy", (0, 15)),
            ("10.7774/cevr.2016.5.1.19", "10.7774/cevr.2016.5.1.19", (0, 24)),
            ("10.5594/SMPTE.ST2067-21.2020", "10.5594/smpte.st2067-21.2020", (0, 28)),
            ("10.1038/a%2Fb", "10.1038/a%2fb", (0, 13)),
            (
                "https://doi.org/10.1038/nature12345",
                "10.1038/nature12345",
                (0, 35),
            ),
            (
                "http://dx.doi.org/10.1000/182",
                "10.1000/182",
                (0, 29),
            ),
            (
                "https://www.doi.org/10.1038/nature12345",
                "10.1038/nature12345",
                (0, 39),
            ),
            ("doi:10.1038/nature12345", "10.1038/nature12345", (0, 23)),
            ("DOI: 10.1038/nature12345", "10.1038/nature12345", (0, 24)),
            ("urn:doi:10.1038/nature12345", "10.1038/nature12345", (0, 27)),
            ("info:doi/10.1038/nature12345", "10.1038/nature12345", (0, 28)),
            ("See 10.1038/nature12345.", "10.1038/nature12345", (4, 23)),
        ],
    )
    def test_success_rows(
        self, text: str, expected_value: str, expected_span: tuple[int, int]
    ) -> None:
        """Research vectors canonicalize (Handbook/Crossref/Wikidata)."""
        paxman.register_all_shipped()
        contract = DOICapability.create_contract()
        result = paxman.canonicalize(text, contract)

        assert result.status == Resolution.SUCCESS
        assert result.canonicalized_value == expected_value
        assert result.span == expected_span
        assert {c.value for c in result.candidates} == {expected_value}
        for candidate in result.candidates:
            assert candidate.validation_rule == "Section 4-doi-syntax"
            assert candidate.provenance[0].authority == "ISO"

    def test_url_output_format(self) -> None:
        paxman.register_all_shipped()
        contract = DOICapability.create_contract(output_format="url")
        result = paxman.canonicalize("doi:10.1038/nature12345", contract)

        assert result.status == Resolution.SUCCESS
        assert result.canonicalized_value == "https://doi.org/10.1038/nature12345"


@pytest.mark.integration
class TestDOIPipelineMissing:
    """No 10./slash/suffix, shortDOI, URN-colon DEFER, over-long: no claim."""

    @pytest.mark.parametrize(
        "text",
        [
            "10.1038/",
            "10.1038nature12345",
            "nature12345",
            "20.500.1234/abc",
            "10/gf2p3c",
            "https://doi.org/urn:doi:10.123:456",
            "10.1234567890/x",
            "hello world",
        ],
    )
    def test_missing_rows(self, text: str) -> None:
        paxman.register_all_shipped()
        contract = DOICapability.create_contract()
        result = paxman.canonicalize(text, contract)

        assert result.status == Resolution.MISSING


@pytest.mark.integration
class TestDOIPipelineAmbiguity:
    """Two distinct DOIs fail fast under single_value."""

    def test_two_distinct_raise(self) -> None:
        paxman.register_all_shipped()
        contract = DOICapability.create_contract()
        with pytest.raises(MultipleMentionsError):
            paxman.canonicalize(
                "10.1000/182 then 10.1038/nature12345",
                contract,
            )


@pytest.mark.integration
class TestDOISiblingOverlap:
    """Bare numerics stay clear of Phone/Date; resolver URLs are per-contract."""

    def test_bare_numeric_sibling_clean(self) -> None:
        paxman.register_all_shipped()

        doi_result = paxman.canonicalize("10.1000/182", DOICapability.create_contract())
        assert doi_result.status == Resolution.SUCCESS

        assert (
            paxman.canonicalize("10.1000/182", PhoneCapability.create_contract()).status
            == Resolution.MISSING
        )
        assert (
            paxman.canonicalize("10.1000/182", DateCapability.create_contract()).status
            == Resolution.MISSING
        )

    def test_resolver_url_overlap_documented(self) -> None:
        paxman.register_all_shipped()
        text = "https://doi.org/10.1038/nature12345"

        doi_result = paxman.canonicalize(text, DOICapability.create_contract())
        assert doi_result.status == Resolution.SUCCESS
        assert doi_result.canonicalized_value == "10.1038/nature12345"

        url_result = paxman.canonicalize(text, URLCapability.create_contract())
        assert url_result.status == Resolution.SUCCESS
        assert url_result.canonicalized_value == text


@pytest.mark.integration
class TestDOIPipelineContract:
    """Temporal filtering and format policy."""

    def test_year_filter_invalid(self) -> None:
        paxman.register_all_shipped()
        contract = DOICapability.create_contract(year=2020)
        result = paxman.canonicalize("10.1038/nature12345", contract)

        assert result.status == Resolution.INVALID

    def test_unoffered_format_contract_error(self) -> None:
        with pytest.raises(ContractError):
            DOICapability.create_contract(output_format="upper")

    def test_determinism_spot_check(self) -> None:
        paxman.register_all_shipped()
        contract = DOICapability.create_contract()
        first = paxman.canonicalize("DOI: 10.1038/NATURE12345.", contract)
        second = paxman.canonicalize("DOI: 10.1038/NATURE12345.", contract)

        assert first.status == Resolution.SUCCESS
        assert (
            first.canonicalized_value
            == second.canonicalized_value
            == ("10.1038/nature12345")
        )
        assert first.span == second.span == (0, 24)
