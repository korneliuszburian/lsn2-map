"""Export enriched data to XLSX, CSV, GeoJSON, exceptions, and run summary."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import geopandas as gpd
import pandas as pd



EXPORT_COLUMNS = [
    "deployment_id", "client_id", "client_name", "country_code",
    "postal_code_raw", "postal_code_norm", "geo_key",
    "generator_count", "generator_model", "install_status",
    "install_date", "service_region", "account_manager",
    "latitude", "longitude", "geocode_source", "geocode_quality",
    "geocode_status", "map_ready", "exception_reason",
]


def export_outputs(
    enriched: pd.DataFrame,
    exceptions: pd.DataFrame,
    output_dir: str,
    input_row_count: int,
) -> dict:
    """Export all outputs and return a run summary dict."""
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    # Reorder columns
    cols = [c for c in EXPORT_COLUMNS if c in enriched.columns]
    enriched = enriched[cols].copy()

    # Enriched Excel
    enriched.to_excel(out / "clients_enriched.xlsx", index=False, engine="openpyxl")

    # Geocoded CSV
    geocoded = enriched[enriched["geocode_status"] == "matched"].copy()
    geocoded.to_csv(out / "clients_geocoded.csv", index=False)

    # GeoJSON (EPSG:4326)
    _export_geojson(geocoded, out / "clients.geojson")

    # Exceptions CSV
    exceptions.to_csv(out / "geocode_exceptions.csv", index=False)

    # Run summary
    matched = (enriched["geocode_status"] == "matched").sum()
    total = len(enriched)
    match_rate = matched / total if total > 0 else 0.0
    summary = {
        "run_timestamp": datetime.now(timezone.utc).isoformat(),
        "input_row_count": input_row_count,
        "output_row_count": total,
        "matched_count": int(matched),
        "unmatched_count": int(total - matched),
        "match_rate": round(match_rate, 4),
        "exception_count": len(exceptions),
        "qa_flags": exceptions["qa_flag"].value_counts().to_dict() if len(exceptions) else {},
    }
    with open(out / "run_summary.json", "w") as f:
        json.dump(summary, f, indent=2)

    return summary


def _export_geojson(df: pd.DataFrame, path: Path) -> None:
    """Export matched rows as GeoJSON with EPSG:4326."""
    geo = gpd.GeoDataFrame(
        df,
        geometry=gpd.points_from_xy(df["longitude"], df["latitude"]),
        crs="EPSG:4326",
    )
    # Drop columns that don't serialize well
    drop_cols = ["latitude", "longitude"]
    props = geo.drop(columns=[c for c in drop_cols if c in geo.columns and c != "geometry"])
    props.to_file(path, driver="GeoJSON")
