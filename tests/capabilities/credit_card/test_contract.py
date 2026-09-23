"""Tests for CreditCardContract."""

import pytest

from paxman.capabilities.CreditCard.contract import CreditCardContract
from paxman.core.errors import ContractError

pytestmark = [pytest.mark.capability]


def test_default_pan_offered_grouped():
    c = CreditCardContract()
    assert c.output_format == "pan"
    assert CreditCardContract.DEFAULT_OUTPUT_FORMAT == "pan"
    assert frozenset({"grouped"}) == CreditCardContract.OFFERED_OUTPUT_FORMATS
    assert CreditCardContract(output_format="grouped").output_format == "grouped"
    assert CreditCardContract(output_format="default").output_format == "pan"


def test_unknown_format_contract_error():
    with pytest.raises(ContractError):
        CreditCardContract(output_format="bogus")


def test_grouped_class_encoding_declared():
    doc = CreditCardContract.__doc__ or ""
    # ADR-0011 scan: one blank-line-delimited paragraph must name both the
    # offered format and its class. grouped is an encoding (re-chunk of the
    # same digits), never a projection (information is preserved exactly).
    paragraphs = doc.split("\n\n")
    encoding_para = [p for p in paragraphs if "encoding" in p]
    assert encoding_para, "no paragraph declares an ADR-0011 class"
    para = encoding_para[0]
    assert "grouped" in para
    assert "projection" not in doc


def test_suppress_common_words_default_false():
    assert CreditCardContract().suppress_common_words is False


def test_include_brand_validation_default_false():
    assert CreditCardContract().include_brand_validation is False
    assert (
        CreditCardContract(include_brand_validation=True).include_brand_validation
        is True
    )
