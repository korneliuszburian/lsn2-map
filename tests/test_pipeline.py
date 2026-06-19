"""Integration tests for the full pipeline."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from src.clean_clients import clean_clients
from src.enrich import enrich_clients
from src.export import export_outputs
from src.postal_reference import build_mock_reference_from_clients, load_postal_reference
from src.qa import run_quality_checks


SAMPLE_EXCEL = "data/sample/north_america_generator_mapping_template.xlsx"


class TestCleanClients:
    @pytest.mark.skipif(not Path(SAMPLE_EXCEL).exists(), reason="Template Excel not found")
    def test_row_count_preserved(self):
        df = clean_clients(SAMPLE_EXCEL)
        assert len(df) == 1200

    @pytest.mark.skipif(not Path(SAMPLE_EXCEL).exists(), reason="Template Excel not found")
    def test_country_codes_normalized(self):
        df = clean_clients(SAMPLE_EXCEL)
        assert set(df["country_code"].dropna().unique()) <= {"US", "CA", "MX"}

    @pytest.mark.skipif(not Path(SAMPLE_EXCEL).exists(), reason="Template Excel not found")
    def test_geo_key_format(self):
        df = clean_clients(SAMPLE_EXCEL)
        valid = df.dropna(subset=["geo_key"])
        assert all(valid["geo_key"].str.contains("|"))

    @pytest.mark.skipif(not Path(SAMPLE_EXCEL).exists(), reason="Template Excel not found")
    def test_postal_code_as_string(self):
        df = clean_clients(SAMPLE_EXCEL)
        leading_zero = df[df["postal_code_raw"].str.startswith("0")]
        if not leading_zero.empty:
            assert all(leading_zero["postal_code_raw"].str.match(r"^0\d+"))


class TestEnrichAndQA:
    def test_enrich_with_mock_reference(self, sample_clients):
        from src.clean_clients import normalize_countries, normalize_postals
        clients = normalize_postals(normalize_countries(sample_clients))
        ref = build_mock_reference_from_clients(clients)
        enriched = enrich_clients(clients, ref)
        assert len(enriched) == len(clients)
        matched = (enriched["geocode_status"] == "matched").sum()
        assert matched > 0

    def test_qa_flags_bad_postal(self, sample_clients):
        from src.clean_clients import normalize_countries, normalize_postals
        clients = normalize_postals(normalize_countries(sample_clients))
        ref = build_mock_reference_from_clients(clients)
        enriched = enrich_clients(clients, ref)
        exceptions = run_quality_checks(enriched)
        # "bad-code" should produce an invalid_postal_format
        bad = exceptions[exceptions["deployment_id"] == "D006"]
        assert len(bad) > 0


class TestReferenceModes:
    @pytest.mark.skipif(not Path(SAMPLE_EXCEL).exists(), reason="Template Excel not found")
    def test_mock_mode_matches_sample_workbook(self):
        clients = clean_clients(SAMPLE_EXCEL)
        reference = load_postal_reference(
            excel_path=SAMPLE_EXCEL,
            clients=clients,
            reference_mode="mock",
        )
        enriched = enrich_clients(clients, reference)

        matched = (enriched["geocode_status"] == "matched").sum()
        assert matched == 1200

    def test_auto_mode_loads_explicit_reference(self, tmp_path):
        reference_path = tmp_path / "reference.csv"
        pd.DataFrame(
            [
                {
                    "country_code": "US",
                    "postal_code_norm": "10001",
                    "geo_key": "US|10001",
                    "latitude": 40.750633,
                    "longitude": -73.997177,
                    "geocode_source": "TEST",
                    "geocode_quality": "test_centroid",
                }
            ]
        ).to_csv(reference_path, index=False)

        reference = load_postal_reference(reference_path=str(reference_path))

        assert reference["geo_key"].to_list() == ["US|10001"]
        assert reference["geocode_source"].to_list() == ["TEST"]

    def test_parquet_mode_requires_reference_file(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            load_postal_reference(
                reference_path=str(tmp_path / "missing.parquet"),
                reference_mode="parquet",
            )


class TestExport:
    def test_export_creates_files(self, sample_clients, tmp_path):
        from src.clean_clients import normalize_countries, normalize_postals
        clients = normalize_postals(normalize_countries(sample_clients))
        ref = build_mock_reference_from_clients(clients)
        enriched = enrich_clients(clients, ref)
        exceptions = run_quality_checks(enriched)
        summary = export_outputs(enriched, exceptions, str(tmp_path), len(clients))

        assert (tmp_path / "clients_enriched.xlsx").exists()
        assert (tmp_path / "clients_geocoded.csv").exists()
        assert (tmp_path / "clients.geojson").exists()
        assert (tmp_path / "geocode_exceptions.csv").exists()
        assert (tmp_path / "run_summary.json").exists()
        assert summary["input_row_count"] == len(clients)
        assert summary["output_row_count"] == len(clients)


class TestEndToEnd:
    @pytest.mark.skipif(not Path(SAMPLE_EXCEL).exists(), reason="Template Excel not found")
    def test_full_pipeline(self, tmp_path):
        clients = clean_clients(SAMPLE_EXCEL)
        assert len(clients) == 1200

        from src.postal_reference import load_mock_reference
        reference = load_mock_reference(SAMPLE_EXCEL)
        enriched = enrich_clients(clients, reference)
        assert len(enriched) == 1200

        exceptions = run_quality_checks(enriched)
        summary = export_outputs(enriched, exceptions, str(tmp_path), 1200)

        assert summary["input_row_count"] == 1200
        assert summary["output_row_count"] == 1200
        assert summary["match_rate"] >= 0.98

        # GeoJSON must be valid
        import json  # noqa: F811
        geojson = json.loads((tmp_path / "clients.geojson").read_text())
        assert geojson["type"] == "FeatureCollection"
        assert len(geojson["features"]) > 0
