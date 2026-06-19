"""Load postal geocode reference data (parquet, mock, or synthetic)."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

import pandas as pd

ReferenceMode = Literal["auto", "mock", "parquet", "synthetic"]
DEFAULT_REFERENCE_PATH = Path("data/reference/postal_reference.parquet")

REFERENCE_COLUMNS = [
    "country_code", "postal_code_norm", "geo_key",
    "latitude", "longitude", "geocode_source", "geocode_quality",
    "source_version", "updated_at",
]


def load_parquet_reference(path: str) -> pd.DataFrame:
    """Load reference from a parquet file built by build_reference.py."""
    df = pd.read_parquet(path, dtype_backend="pyarrow")
    if "postal_code_norm" in df.columns:
        df["postal_code_norm"] = df["postal_code_norm"].astype(str)
    return df


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
    reference_path: str | None = None,
    excel_path: str | None = None,
    sheet: str = "02_Postal_Reference_MOCK",
    clients: pd.DataFrame | None = None,
    reference_mode: ReferenceMode = "auto",
) -> pd.DataFrame:
    """Load postal reference for demo or production runs.

    Modes:
    - auto: explicit path > default parquet > Excel mock > synthetic.
    - mock: force the workbook mock sheet.
    - parquet: force explicit/default parquet or CSV reference file.
    - synthetic: force generated dev-only coordinates from input rows.

    When loading from parquet, also checks if Excel mock is available to
    supplement missing countries (e.g., MX which has no free geocode source).
    """
    if reference_mode == "mock":
        if not excel_path:
            raise ValueError("reference_mode='mock' requires excel_path")
        print(f"  Loading mock reference from Excel sheet '{sheet}'")
        return load_mock_reference(excel_path, sheet)

    if reference_mode == "synthetic":
        if clients is None:
            raise ValueError("reference_mode='synthetic' requires clients")
        print("  Building synthetic reference from client data")
        return build_mock_reference_from_clients(clients)

    if reference_mode == "parquet":
        path = Path(reference_path) if reference_path else DEFAULT_REFERENCE_PATH
        ref = _load_reference_file(path)
        return _supplement_from_mock(ref, excel_path, sheet)

    if reference_mode != "auto":
        raise ValueError(f"Unsupported reference_mode: {reference_mode}")

    # 1. Explicit reference file (parquet or CSV)
    if reference_path:
        ref = _load_reference_file(Path(reference_path))
        return _supplement_from_mock(ref, excel_path, sheet)

    # 2. Default parquet location
    if DEFAULT_REFERENCE_PATH.exists():
        ref = _load_reference_file(DEFAULT_REFERENCE_PATH)
        return _supplement_from_mock(ref, excel_path, sheet)

    # 3. Excel mock sheet
    if excel_path:
        try:
            print(f"  Loading mock reference from Excel sheet '{sheet}'")
            return load_mock_reference(excel_path, sheet)
        except (ValueError, KeyError):
            pass

    # 4. Synthetic from clients
    if clients is not None:
        print("  Building synthetic reference from client data")
        return build_mock_reference_from_clients(clients)

    raise ValueError("No reference source available. Run 'make reference' or provide --reference path.")


def _load_reference_file(path: Path) -> pd.DataFrame:
    """Load an explicit parquet or CSV reference file."""
    if not path.exists():
        raise FileNotFoundError(f"Reference file not found: {path}")
    print(f"  Loading reference from {path}")
    if path.suffix == ".parquet":
        return load_parquet_reference(str(path))
    return pd.read_csv(path, dtype={"postal_code_norm": str})


def _supplement_from_mock(ref: pd.DataFrame, excel_path: str | None, sheet: str) -> pd.DataFrame:
    """Supplement parquet reference with mock data for countries missing from real sources."""
    if not excel_path:
        return ref
    countries_in_ref = set(ref["country_code"].unique())
    missing = {"US", "CA", "MX"} - countries_in_ref
    if not missing:
        return ref
    try:
        mock = load_mock_reference(excel_path, sheet)
        supplement = mock[mock["country_code"].isin(missing)]
        if supplement.empty:
            return ref
        print(f"  Supplementing {len(supplement)} mock entries for: {', '.join(sorted(missing))}")
        return pd.concat([ref, supplement], ignore_index=True).drop_duplicates(subset="geo_key", keep="first")
    except (ValueError, KeyError):
        return ref
