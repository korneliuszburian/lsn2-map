# North America Generator Deployment Mapping Pipeline

Geocode ~1200 generator deployments across US/CA/MX from Excel input. Produces enriched Excel, CSV, GeoJSON (EPSG:4326), QA reports, and run summary.

## Quick Start

```bash
# Setup
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Run with sample data
make run

# Or directly
python src/run_pipeline.py --input data/sample/north_america_generator_mapping_template.xlsx --output data/output
```

## Commands

| Command | Description |
|---------|-------------|
| `make run` | Run pipeline with sample data |
| `make test` | Run all tests |
| `make lint` | Lint with ruff |
| `make typecheck` | Type check with pyright |
| `make clean` | Remove output files |
| `make all` | Lint + test + run |

## Pipeline Steps

1. **Load** — Read Excel, treat postal codes as text
2. **Normalize** — Country → ISO (US/CA/MX), postal codes → canonical format
3. **Reference** — Load postal geocode reference (mock from template Excel)
4. **Enrich** — Left-join on `geo_key` (country + postal)
5. **QA** — Flag missing/invalid/unmatched/bounds violations
6. **Export** — XLSX, CSV, GeoJSON, exceptions CSV, run summary JSON

## Output Files

| File | Description |
|------|-------------|
| `clients_enriched.xlsx` | All rows with lat/lon and status |
| `clients_geocoded.csv` | Matched rows only |
| `clients.geojson` | GeoJSON EPSG:4326 for Power BI / Mapbox / QGIS |
| `geocode_exceptions.csv` | Unmatched/invalid rows |
| `run_summary.json` | Match rate, counts, QA flags |

## Postal Code Normalization

| Country | Format | Example |
|---------|--------|---------|
| US | 5 digits (ZIP+4 → first 5) | `10001-1234` → `10001`, `02108` → `02108` |
| CA | A1A1A1 (strip spaces/hyphens) | `K1A 0B1` → `K1A0B1`, `M5H-2N2` → `M5H2N2` |
| MX | 5 digits | `06600` → `06600`, `01000` → `01000` |

## Production Notes

The template uses **mock geocode data**. For production:

- **US**: Replace with Census TIGER/Line ZCTA5 centroids
- **CA**: Replace with Statistics Canada PCCF or Canada Post data
- **MX**: Replace with SEPOMEX / datos.gob.mx postal shapefiles
- **Fallback**: Set `MAPBOX_TOKEN` env var for Mapbox Permanent Geocoding on unmatched

## Architecture

```
src/
  run_pipeline.py       CLI entry point
  clean_clients.py      Load + normalize
  normalize_postal.py   US/CA/MX postal normalization
  postal_reference.py   Mock + real reference loading
  enrich.py             Join clients to reference
  qa.py                 Quality checks
  export.py             XLSX/CSV/GeoJSON/JSON export
tests/
  test_normalize_postal.py   25 unit tests
  test_pipeline.py            8 integration tests
```

## Power BI Setup

Use latitude/longitude columns directly. Do not let BI guess by postal code.

- **Tooltip**: client_name, postal_code_norm, generator_model, service_region
- **Legend**: install_status
- **Size**: generator_count
