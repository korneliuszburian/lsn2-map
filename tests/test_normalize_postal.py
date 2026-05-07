"""Unit tests for postal and country normalization."""

from __future__ import annotations

from src.normalize_postal import (
    normalize_country,
    normalize_postal,
    normalize_postal_ca,
    normalize_postal_mx,
    normalize_postal_us,
)


class TestNormalizeCountry:
    def test_us_variants(self):
        assert normalize_country("US") == "US"
        assert normalize_country("USA") == "US"
        assert normalize_country("United States") == "US"
        assert normalize_country("united states of america") == "US"

    def test_ca_variants(self):
        assert normalize_country("CA") == "CA"
        assert normalize_country("CAN") == "CA"
        assert normalize_country("Canada") == "CA"

    def test_mx_variants(self):
        assert normalize_country("MX") == "MX"
        assert normalize_country("MEX") == "MX"
        assert normalize_country("Mexico") == "MX"
        assert normalize_country("México") == "MX"

    def test_none_and_empty(self):
        assert normalize_country(None) is None
        assert normalize_country("") is None
        assert normalize_country("  ") is None

    def test_unknown(self):
        assert normalize_country("DE") is None


class TestNormalizePostalUS:
    def test_basic_5digit(self):
        assert normalize_postal_us("10001") == "10001"

    def test_zip_plus4(self):
        assert normalize_postal_us("10001-1234") == "10001"

    def test_leading_zero(self):
        assert normalize_postal_us("02108") == "02108"

    def test_none_and_empty(self):
        assert normalize_postal_us(None) is None
        assert normalize_postal_us("") is None

    def test_invalid(self):
        assert normalize_postal_us("ABCDE") is None


class TestNormalizePostalCA:
    def test_valid_no_space(self):
        assert normalize_postal_ca("K1A0B1") == "K1A0B1"

    def test_valid_with_space(self):
        assert normalize_postal_ca("K1A 0B1") == "K1A0B1"

    def test_valid_lowercase(self):
        assert normalize_postal_ca("k1a0b1") == "K1A0B1"

    def test_valid_with_hyphen(self):
        assert normalize_postal_ca("M5H-2N2") == "M5H2N2"

    def test_invalid_format(self):
        assert normalize_postal_ca("12345") is None
        assert normalize_postal_ca("ABCDE") is None

    def test_none_and_empty(self):
        assert normalize_postal_ca(None) is None
        assert normalize_postal_ca("") is None


class TestNormalizePostalMX:
    def test_basic_5digit(self):
        assert normalize_postal_mx("06600") == "06600"

    def test_leading_zero(self):
        assert normalize_postal_mx("01000") == "01000"

    def test_none_and_empty(self):
        assert normalize_postal_mx(None) is None
        assert normalize_postal_mx("") is None

    def test_invalid(self):
        assert normalize_postal_mx("ABC") is None


class TestNormalizePostalDispatch:
    def test_us_dispatch(self):
        assert normalize_postal("US", "02108") == "02108"

    def test_ca_dispatch(self):
        assert normalize_postal("CA", "K1A 0B1") == "K1A0B1"

    def test_mx_dispatch(self):
        assert normalize_postal("MX", "06600") == "06600"

    def test_unknown_country(self):
        assert normalize_postal("DE", "12345") is None

    def test_none_country(self):
        assert normalize_postal(None, "12345") is None
