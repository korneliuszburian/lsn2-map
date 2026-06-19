"""Download and build postal geocode reference from real sources.

Sources:
  US — Census TIGER/Line ZCTA520 (2024)
  CA — GeoNames CA_full
  MX — GeoNames MX

Usage:
  python -m src.build_reference --output data/reference/postal_reference.parquet
  python -m src.build_reference --output data/reference/postal_reference.parquet --force
"""

from __future__ import annotations

import argparse
import tempfile
import zipfile
from pathlib import Path

import geopandas as gpd
import pandas as pd
import requests

SOURCES = {
    "us": "https://www2.census.gov/geo/tiger/TIGER2024/ZCTA520/tl_2024_us_zcta520.zip",
    "ca": "https://download.geonames.org/export/zip/CA_full.csv.zip",
    "mx": "https://download.geonames.org/export/zip/MX.zip",
}

GEONAMES_COLUMNS = [
    "country_code", "postal_code", "place_name",
    "admin_name1", "admin_code1", "admin_name2", "admin_code2",
    "admin_name3", "admin_code3", "latitude", "longitude", "accuracy",
]


def _download(url: str, dest: Path, force: bool = False) -> Path:
    if dest.exists() and not force:
        print(f"  Cached: {dest.name}")
        return dest
    print(f"  Downloading {url}...")
    resp = requests.get(url, stream=True, timeout=300)
    resp.raise_for_status()
    total = int(resp.headers.get("content-length", 0))
    with open(dest, "wb") as f:
        downloaded = 0
        for chunk in resp.iter_content(chunk_size=1 << 20):
            f.write(chunk)
            downloaded += len(chunk)
            if total:
                mb = downloaded / (1 << 20)
                total_mb = total / (1 << 20)
                print(f"\r  {mb:.0f}/{total_mb:.0f} MB", end="", flush=True)
    print()
    return dest


def build_us(cache_dir: Path, force: bool = False) -> pd.DataFrame:
    """Build US reference from Census TIGER/Line ZCTA520 shapefile."""
    zip_path = _download(SOURCES["us"], cache_dir / "tl_2024_us_zcta520.zip", force)
    print("  Reading US shapefile...")
    gdf = gpd.read_file(zip_path)
    df = pd.DataFrame({
        "country_code": "US",
        "postal_code_norm": gdf["ZCTA5CE20"].astype(str),
        "latitude": gdf["INTPTLAT20"].astype(float),
        "longitude": gdf["INTPTLON20"].astype(float),
    })
    df["geo_key"] = "US|" + df["postal_code_norm"]
    df["geocode_source"] = "US_CENSUS_ZCTA520_2024"
    df["geocode_quality"] = "census_centroid"
    df["source_version"] = "TIGER2024"
    df["updated_at"] = pd.Timestamp.now(tz="UTC").strftime("%Y-%m-%d")
    print(f"  US: {len(df):,} ZIP codes")
    return df


def build_ca(cache_dir: Path, force: bool = False) -> pd.DataFrame:
    """Build CA reference from GeoNames CA_full."""
    zip_path = _download(SOURCES["ca"], cache_dir / "CA_full.csv.zip", force)
    with zipfile.ZipFile(zip_path) as zf:
        csv_name = [n for n in zf.namelist() if n.endswith(".txt")][0]
        with zf.open(csv_name) as f:
            raw = pd.read_csv(f, sep="\t", header=None, names=GEONAMES_COLUMNS, dtype={"postal_code": str})
    df = pd.DataFrame({
        "country_code": "CA",
        "postal_code_norm": raw["postal_code"].str.upper().str.replace(r"[\s-]", "", regex=True),
        "latitude": raw["latitude"].astype(float),
        "longitude": raw["longitude"].astype(float),
    })
    df["geo_key"] = "CA|" + df["postal_code_norm"]
    df["geocode_source"] = "GEONAMES_CA_FULL"
    df["geocode_quality"] = "geonames_centroid"
    df["source_version"] = "GEONAMES_2026"
    df["updated_at"] = pd.Timestamp.now(tz="UTC").strftime("%Y-%m-%d")
    print(f"  CA: {len(df):,} postal codes")
    return df


def build_mx(cache_dir: Path, force: bool = False) -> pd.DataFrame:
    """Build MX reference from GeoNames MX.

    Note: GeoNames MX.zip often contains only a readme with no postal data.
    In that case, returns an empty DataFrame with correct schema.
    Production MX data requires SEPOMEX + coordinate enrichment (separate step).
    """
    zip_path = _download(SOURCES["mx"], cache_dir / "MX.zip", force)
    with zipfile.ZipFile(zip_path) as zf:
        csv_name = [n for n in zf.namelist() if n.endswith(".txt") and n != "readme.txt"][0]
        with zf.open(csv_name) as f:
            raw = pd.read_csv(f, sep="\t", header=None, names=GEONAMES_COLUMNS, dtype={"postal_code": str})
    # GeoNames MX often has no real data (just a readme)
    if raw.empty or raw["latitude"].isna().all():
        print("  MX: No GeoNames data available (known gap). Returning empty.")
        return pd.DataFrame(columns=[
            "country_code", "postal_code_norm", "geo_key",
            "latitude", "longitude", "geocode_source", "geocode_quality",
            "source_version", "updated_at",
        ])
    df = pd.DataFrame({
        "country_code": "MX",
        "postal_code_norm": raw["postal_code"].str.strip(),
        "latitude": raw["latitude"].astype(float),
        "longitude": raw["longitude"].astype(float),
    })
    df["geo_key"] = "MX|" + df["postal_code_norm"]
    df["geocode_source"] = "GEONAMES_MX"
    df["geocode_quality"] = "geonames_centroid"
    df["source_version"] = "GEONAMES_2026"
    df["updated_at"] = pd.Timestamp.now(tz="UTC").strftime("%Y-%m-%d")
    print(f"  MX: {len(df):,} postal codes")
    return df


def build_all(output_path: str, force: bool = False) -> None:
    """Download all sources and build combined reference parquet."""
    cache_dir = Path(output_path).parent
    cache_dir.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)

        print("Building US reference...")
        us = build_us(tmp_path, force)

        print("Building CA reference...")
        ca = build_ca(tmp_path, force)

        print("Building MX reference...")
        mx = build_mx(tmp_path, force)

    print("Combining references...")
    combined = pd.concat([us, ca, mx], ignore_index=True)
    combined = combined.drop_duplicates(subset="geo_key", keep="first")
    combined = combined.sort_values("geo_key").reset_index(drop=True)

    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    combined.to_parquet(out, index=False)
    print(f"Saved {len(combined):,} records to {out}")
    print(f"  US: {(combined['country_code'] == 'US').sum():,}")
    print(f"  CA: {(combined['country_code'] == 'CA').sum():,}")
    print(f"  MX: {(combined['country_code'] == 'MX').sum():,}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Build postal geocode reference from real sources")
    parser.add_argument("--output", default="data/reference/postal_reference.parquet", help="Output parquet path")
    parser.add_argument("--force", action="store_true", help="Re-download even if cached")
    args = parser.parse_args()
    build_all(args.output, args.force)


if __name__ == "__main__":
    main()
