"""Quality-assurance checks on enriched client data."""

from __future__ import annotations

import pandas as pd

# Rough coordinate bounds per country
BOUNDS = {
    "US": {"lat": (18, 72), "lon": (-180, -60)},
    "CA": {"lat": (41, 84), "lon": (-142, -50)},
    "MX": {"lat": (14, 33), "lon": (-119, -86)},
}


def run_quality_checks(df: pd.DataFrame) -> pd.DataFrame:
    """Return a DataFrame of QA exception rows with an added `qa_flag` column."""
    exceptions: list[pd.DataFrame] = []

    def _flag(mask: pd.Series, flag: str) -> None:
        if mask.any():
            rows = df.loc[mask].copy()
            rows["qa_flag"] = flag
            exceptions.append(rows)

    _flag(df["country_code"].isna(), "missing_country")
    _flag(df["postal_code_raw"].isna() | (df["postal_code_raw"] == ""), "missing_postal")
    _flag(df["postal_code_norm"].isna() & df["country_code"].notna(), "invalid_postal_format")
    _flag(df["geocode_status"] == "unmatched", "postal_not_found")
    _flag(df.duplicated(subset=["client_id"], keep=False), "duplicate_client_id")
    _flag(df.duplicated(subset=["geo_key"], keep=False) & df["geo_key"].notna(), "duplicate_geo_key")
    _flag(_out_of_bounds(df), "lat_lon_out_of_bounds")

    if not exceptions:
        return pd.DataFrame(columns=list(df.columns) + ["qa_flag"])
    return pd.concat(exceptions, ignore_index=True).drop_duplicates(subset=["deployment_id", "qa_flag"])


def _out_of_bounds(df: pd.DataFrame) -> pd.Series:
    mask = pd.Series(False, index=df.index)
    matched = df[df["latitude"].notna() & df["country_code"].notna()]
    for cc, bounds in BOUNDS.items():
        subset = matched["country_code"] == cc
        if not subset.any():
            continue
        lat_ok = matched.loc[subset, "latitude"].between(bounds["lat"][0], bounds["lat"][1])
        lon_ok = matched.loc[subset, "longitude"].between(bounds["lon"][0], bounds["lon"][1])
        bad = subset & ~(lat_ok.reindex(df.index, fill_value=True) & lon_ok.reindex(df.index, fill_value=True))
        mask = mask | bad
    return mask
