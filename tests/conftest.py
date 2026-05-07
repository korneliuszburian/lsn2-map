"""Shared test fixtures."""

from __future__ import annotations

import pandas as pd
import pytest


@pytest.fixture
def sample_clients() -> pd.DataFrame:
    return pd.DataFrame({
        "deployment_id": ["D001", "D002", "D003", "D004", "D005", "D006"],
        "client_id": ["C001", "C002", "C003", "C004", "C005", "C006"],
        "client_name": ["A", "B", "C", "D", "E", "F"],
        "country_code": ["US", "US", "CA", "CA", "MX", "US"],
        "postal_code_raw": ["10001-1234", "02108", "K1A0B1", "M5H 2N2", "06600", "bad-code"],
        "generator_count": [1, 2, 1, 1, 3, 1],
        "generator_model": ["GX-500", "GX-250", "GX-500", "Hybrid-X", "GX-500", "GX-250"],
        "install_status": ["Deployed", "Deployed", "Service Due", "Deployed", "Deployed", "Deployed"],
        "install_date": pd.to_datetime(["2024-01-01"] * 6),
        "service_region": ["NE", "NE", "ON", "ON", "CDMX", "NE"],
        "account_manager": ["X", "X", "Y", "Y", "Z", "X"],
    })
