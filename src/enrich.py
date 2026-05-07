"""Enrich client data with geocode coordinates from postal reference."""

from __future__ import annotations

import pandas as pd


def enrich_clients(clients: pd.DataFrame, reference: pd.DataFrame) -> pd.DataFrame:
    """Left-join clients to postal reference on geo_key.

    Adds: latitude, longitude, geocode_source, geocode_quality.
    Adds: geocode_status (matched/unmatched), map_ready (yes/no).
    """
    ref_cols = ["geo_key", "latitude", "longitude", "geocode_source", "geocode_quality"]
    ref_subset = reference[ref_cols].drop_duplicates("geo_key")

    enriched = clients.merge(ref_subset, on="geo_key", how="left")

    enriched["geocode_status"] = enriched["latitude"].notna().map({True: "matched", False: "unmatched"})
    enriched["map_ready"] = enriched["geocode_status"].map({"matched": "yes", "unmatched": "no"})
    enriched["exception_reason"] = enriched.apply(_exception_reason, axis=1)

    return enriched


def _exception_reason(row: pd.Series) -> str:
    if row["geocode_status"] == "matched":
        return "ok"
    if pd.isna(row.get("country_code")):
        return "missing_country"
    if pd.isna(row.get("postal_code_norm")):
        return "missing_postal"
    if pd.isna(row.get("latitude")):
        return "postal_not_found"
    return "unknown"
