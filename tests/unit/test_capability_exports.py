"""Tests for capability exports."""

from __future__ import annotations

import pytest

from paxman.capabilities import (  # isort: skip
    BIC,
    Coordinates,
    Country,
    Currency,
    Date,
    Email,
    IBAN,
    IP,
    ISBN,
    ISSN,
    Language,
    MacAddress,
    Money,
    ORCID,
    Phone,
    SIUnit,
    URL,
)


class TestCapabilityExports:
    @pytest.mark.unit
    def test_email_capability_importable(self) -> None:
        """Email capability is importable from paxman.capabilities."""
        assert Email is not None

    @pytest.mark.unit
    def test_email_capability_name(self) -> None:
        """Email capability has correct name."""
        assert Email.name == "email"


class TestBICCapabilityExports:
    @pytest.mark.unit
    def test_bic_capability_importable(self) -> None:
        """BIC capability is importable from paxman.capabilities."""
        assert BIC is not None

    @pytest.mark.unit
    def test_bic_capability_name(self) -> None:
        """BIC capability has correct name."""
        assert BIC.name == "bic"


class TestCountryCapabilityExports:
    @pytest.mark.unit
    def test_country_capability_importable(self) -> None:
        """Country capability is importable from paxman.capabilities."""
        assert Country is not None

    @pytest.mark.unit
    def test_country_capability_name(self) -> None:
        """Country capability has correct name."""
        assert Country.name == "country"


class TestCurrencyCapabilityExports:
    @pytest.mark.unit
    def test_currency_capability_importable(self) -> None:
        """Currency capability is importable from paxman.capabilities."""
        assert Currency is not None

    @pytest.mark.unit
    def test_currency_capability_name(self) -> None:
        """Currency capability has correct name."""
        assert Currency.name == "currency"


class TestDateCapabilityExports:
    @pytest.mark.unit
    def test_date_capability_importable(self) -> None:
        """Date capability is importable from paxman.capabilities."""
        assert Date is not None

    @pytest.mark.unit
    def test_date_capability_name(self) -> None:
        """Date capability has correct name."""
        assert Date.name == "date"


class TestPhoneCapabilityExports:
    @pytest.mark.unit
    def test_phone_capability_importable(self) -> None:
        """Phone capability is importable from paxman.capabilities."""
        assert Phone is not None

    @pytest.mark.unit
    def test_phone_capability_name(self) -> None:
        """Phone capability has correct name."""
        assert Phone.name == "phone"


class TestISBNCapabilityExports:
    @pytest.mark.unit
    def test_isbn_capability_importable(self) -> None:
        """ISBN capability is importable from paxman.capabilities."""
        assert ISBN is not None

    @pytest.mark.unit
    def test_isbn_capability_name(self) -> None:
        """ISBN capability has correct name."""
        assert ISBN.name == "isbn"


class TestISSNCapabilityExports:
    @pytest.mark.unit
    def test_issn_capability_importable(self) -> None:
        """ISSN capability is importable from paxman.capabilities."""
        assert ISSN is not None

    @pytest.mark.unit
    def test_issn_capability_name(self) -> None:
        """ISSN capability has correct name."""
        assert ISSN.name == "issn"


class TestIBANCapabilityExports:
    @pytest.mark.unit
    def test_iban_capability_importable(self) -> None:
        """IBAN capability is importable from paxman.capabilities."""
        assert IBAN is not None

    @pytest.mark.unit
    def test_iban_capability_name(self) -> None:
        """IBAN capability has correct name."""
        assert IBAN.name == "iban"


class TestIPCapabilityExports:
    @pytest.mark.unit
    def test_ip_capability_importable(self) -> None:
        """IP capability is importable from paxman.capabilities."""
        assert IP is not None

    @pytest.mark.unit
    def test_ip_capability_name(self) -> None:
        """IP capability has correct name."""
        assert IP.name == "ip"


class TestMoneyCapabilityExports:
    @pytest.mark.unit
    def test_money_capability_importable(self) -> None:
        """Money capability is importable from paxman.capabilities."""
        assert Money is not None

    @pytest.mark.unit
    def test_money_capability_name(self) -> None:
        """Money capability has correct name."""
        assert Money.name == "money"


class TestORCIDCapabilityExports:
    @pytest.mark.unit
    def test_orcid_capability_importable(self) -> None:
        """ORCID capability is importable from paxman.capabilities."""
        assert ORCID is not None

    @pytest.mark.unit
    def test_orcid_capability_name(self) -> None:
        """ORCID capability has correct name."""
        assert ORCID.name == "orcid"


class TestLanguageCapabilityExports:
    @pytest.mark.unit
    def test_language_capability_importable(self) -> None:
        """Language capability is importable from paxman.capabilities."""
        assert Language is not None

    @pytest.mark.unit
    def test_language_capability_name(self) -> None:
        """Language capability has correct name."""
        assert Language.name == "language"


class TestMacAddressCapabilityExports:
    @pytest.mark.unit
    def test_mac_address_capability_importable(self) -> None:
        """MacAddress capability is importable from paxman.capabilities."""
        assert MacAddress is not None

    @pytest.mark.unit
    def test_mac_address_capability_name(self) -> None:
        """MacAddress capability has correct name."""
        assert MacAddress.name == "mac_address"


class TestCoordinatesCapabilityExports:
    @pytest.mark.unit
    def test_coordinates_capability_importable(self) -> None:
        """Coordinates capability is importable from paxman.capabilities."""
        assert Coordinates is not None

    @pytest.mark.unit
    def test_coordinates_capability_name(self) -> None:
        """Coordinates capability has correct name."""
        assert Coordinates.name == "coordinates"


class TestSIUnitCapabilityExports:
    @pytest.mark.unit
    def test_si_unit_capability_importable(self) -> None:
        """SIUnit capability is importable from paxman.capabilities."""
        assert SIUnit is not None

    @pytest.mark.unit
    def test_si_unit_capability_name(self) -> None:
        """SIUnit capability has correct name."""
        assert SIUnit.name == "si_unit"


class TestURLCapabilityExports:
    @pytest.mark.unit
    def test_url_capability_importable(self) -> None:
        """URL capability is importable from paxman.capabilities."""
        assert URL is not None

    @pytest.mark.unit
    def test_url_capability_name(self) -> None:
        """URL capability has correct name."""
        assert URL.name == "url"

    @pytest.mark.unit
    def test_export_list_contains_all_shipped_names(self) -> None:
        """The lazy export surface lists every shipped capability."""
        import paxman.capabilities as capabilities

        assert set(capabilities.__all__) == {
            "BIC",
            "Coordinates",
            "Country",
            "Currency",
            "Date",
            "Email",
            "IBAN",
            "IP",
            "ISBN",
            "ISSN",
            "Language",
            "MacAddress",
            "Money",
            "ORCID",
            "Phone",
            "SIUnit",
            "URL",
        }
