"""Load raw client Excel and produce a clean DataFrame."""

from __future__ import annotations

import pandas as pd

INPUT_COLUMNS = [
    "deployment_id", "client_id", "client_name", "country_code",
    "postal_code_raw", "generator_count", "generator_model",
    "install_status", "install_date", "service_region", "account_manager",
]


def load_clients(path: str, sheet: str = "01_Clients_Input") -> pd.DataFrame:
    """Load client data from Excel, treating postal_code_raw as text."""
    df = pd.read_excel(
        path,
        sheet_name=sheet,
        dtype={"postal_code_raw": str, "deployment_id": str, "client_id": str},
    )
    # Keep only the expected input columns (ignore pre-computed norm/geo_key if present)
    keep = [c for c in INPUT_COLUMNS if c in df.columns]
    df = df[keep].copy()
    df["postal_code_raw"] = df["postal_code_raw"].astype(str).str.strip()
    return df


def normalize_countries(df: pd.DataFrame) -> pd.DataFrame:
    from src.normalize_postal import normalize_country
    df = df.copy()
    df["country_code"] = df["country_code"].apply(normalize_country)
    return df


def normalize_postals(df: pd.DataFrame) -> pd.DataFrame:
    from src.normalize_postal import normalize_postal
    df = df.copy()
    df["postal_code_norm"] = df.apply(
        lambda r: normalize_postal(r["country_code"], r["postal_code_raw"]), axis=1
    )
    df["geo_key"] = df.apply(
        lambda r: f"{r['country_code']}|{r['postal_code_norm']}"
        if r["country_code"] and r["postal_code_norm"]
        else None,
        axis=1,
    )
    return df


def clean_clients(path: str, sheet: str = "01_Clients_Input") -> pd.DataFrame:
    df = load_clients(path, sheet)
    df = normalize_countries(df)
    df = normalize_postals(df)
    return df
