"""Country and postal-code normalization for US, CA, MX."""

from __future__ import annotations

import re

# Country aliases → canonical ISO codes
_COUNTRY_MAP: dict[str, str] = {
    "US": "US", "USA": "US", "UNITED STATES": "US", "UNITED STATES OF AMERICA": "US",
    "CA": "CA", "CAN": "CA", "CANADA": "CA",
    "MX": "MX", "MEX": "MX", "MEXICO": "MX",
    "MÉXICO": "MX",
}

_CA_PATTERN = re.compile(r"^[A-Z]\d[A-Z]\d[A-Z]\d$")


def normalize_country(raw: str | None) -> str | None:
    if not raw or not str(raw).strip():
        return None
    key = str(raw).strip().upper()
    return _COUNTRY_MAP.get(key)


def normalize_postal_us(raw: str | None) -> str | None:
    if not raw or not str(raw).strip():
        return None
    s = str(raw).strip()
    # ZIP+4: take first 5 digits
    m = re.match(r"^(\d{5})", s)
    return m.group(1) if m else None


def normalize_postal_ca(raw: str | None) -> str | None:
    if not raw or not str(raw).strip():
        return None
    s = str(raw).strip().upper().replace(" ", "").replace("-", "")
    if _CA_PATTERN.match(s):
        return s
    return None


def normalize_postal_mx(raw: str | None) -> str | None:
    if not raw or not str(raw).strip():
        return None
    s = str(raw).strip()
    m = re.match(r"^(\d{5})", s)
    return m.group(1) if m else None


_NORMALIZERS = {
    "US": normalize_postal_us,
    "CA": normalize_postal_ca,
    "MX": normalize_postal_mx,
}


def normalize_postal(country_code: str | None, raw: str | None) -> str | None:
    if not country_code or country_code not in _NORMALIZERS:
        return None
    return _NORMALIZERS[country_code](raw)
