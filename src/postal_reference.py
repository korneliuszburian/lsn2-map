"""Load postal geocode reference data (mock or production)."""

from __future__ import annotations

from datetime import datetime, timezone

import pandas as pd

REFERENCE_COLUMNS = [
    "country_code", "postal_code_norm", "geo_key",
    "latitude", "longitude", "geocode_source", "geocode_quality",
    "source_version", "updated_at",
]


def load_mock_reference(path: str, sheet: str = "02_Postal_Reference_MOCK") -> pd.DataFrame:
    """Load mock postal reference from the template Excel."""
    df = pd.read_excel(path, sheet_name=sheet, dtype={"postal_code_norm": str})
    keep = [c for c in REFERENCE_COLUMNS if c in df.columns]
    df = df[keep].copy()
    return df


def build_mock_reference_from_clients(clients: pd.DataFrame) -> pd.DataFrame:
    """Build a minimal mock reference from unique geo_keys in the client data.

    Generates synthetic centroids within valid country bounds.
    Use only for development/testing.
    """
    import numpy as np

    unique = clients.dropna(subset=["geo_key"]).drop_duplicates("geo_key")[
        ["country_code", "postal_code_norm", "geo_key"]
    ].copy()

    bounds = {
        "US": {"lat": (25, 48), "lon": (-125, -67)},
        "CA": {"lat": (42, 70), "lon": (-141, -52)},
        "MX": {"lat": (15, 32), "lon": (-118, -87)},
    }

    rng = np.random.default_rng(42)

    def _random_coords(row):
        b = bounds.get(row["country_code"], bounds["US"])
        lat = rng.uniform(b["lat"][0], b["lat"][1])
        lon = rng.uniform(b["lon"][0], b["lon"][1])
        return pd.Series({"latitude": round(lat, 6), "longitude": round(lon, 6)})

    coords = unique.apply(_random_coords, axis=1)
    ref = pd.concat([unique, coords], axis=1)
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    ref["geocode_source"] = "MOCK_SYNTHETIC"
    ref["geocode_quality"] = "synthetic_mock"
    ref["source_version"] = f"MOCK_{now}"
    ref["updated_at"] = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    return ref


def load_postal_reference(
    excel_path: str | None = None,
    sheet: str = "02_Postal_Reference_MOCK",
    clients: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """Load postal reference. Tries Excel sheet first, falls back to synthetic mock."""
    if excel_path:
        try:
            return load_mock_reference(excel_path, sheet)
        except (ValueError, KeyError):
            pass
    if clients is not None:
        return build_mock_reference_from_clients(clients)
    raise ValueError("No reference source available. Provide excel_path or clients.")
