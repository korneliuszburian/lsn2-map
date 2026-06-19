# Project: North America Generator Deployment Mapping Pipeline

## Purpose
Geocode ~1200 generator deployments across US/CA/MX from Excel input.
Produce enriched Excel, CSV, GeoJSON (EPSG:4326), QA reports, and run summary.

## Stack
- Python 3.12
- pandas, geopandas, shapely, pyarrow, openpyxl
- pytest, ruff, pyright

## Commands
All commands require venv: `source .venv/bin/activate`

- Build reference: `make reference` (first run ~2 min, downloads ~504 MB US Census)
- Build client-map prototype: `make prototype`
- Run sample demo data: `make run-demo` (`--reference-mode mock`, expected 1200/1200)
- Run sample against local parquet: `make run-parquet-sample` (expected low match on synthetic sample)
- Run production/client data: `CLIENT_INPUT=data/input/clients.xlsx make run-prod`
- Render map from existing CSV: `make map-options`
- Tests: `make test` or `python -m pytest tests/ -v`
- Lint: `make lint` or `ruff check src/ tests/`
- Typecheck: `make typecheck` or `pyright src/ tests/`
- Clean outputs: `make clean`

## Architecture
- `src/run_pipeline.py` — CLI entry point (run as `python -m src.run_pipeline`)
- `src/build_reference.py` — download real geocode sources, build parquet
- `src/clean_clients.py` — load Excel + normalize countries/postals
- `src/normalize_postal.py` — US/CA/MX postal-code normalization
- `src/postal_reference.py` — load parquet/mock/synthetic reference
- `src/render_lsn_map_options.py` — render standalone Leaflet HTML on supplied LSN artwork
- `src/enrich.py` — left-join clients to reference by geo_key
- `src/qa.py` — quality checks (bounds, duplicates, missing fields)
- `src/export.py` — XLSX/CSV/GeoJSON/JSON export
- `data/reference/` — postal_reference.parquet (gitignored, built by `make reference`)
- `data/assets/client-map/` — committed client/demo map artwork assets
- `data/input/` — raw Excel files (gitignored)
- `data/output/` — generated outputs (gitignored)
- `data/sample/` — template files (committed)
- `tests/` — 36 pytest tests

## Data Rules
- Never commit real client data
- Treat postal_code_raw as text (preserve leading zeros)
- geo_key = country_code + "|" + postal_code_norm
- Target: 98%+ match rate for valid postal codes
- Coordinate bounds: US lat 18..72 lon -180..-60; CA lat 41..84 lon -142..-50; MX lat 14..33 lon -119..-86

## Geocode Sources
- US: Census TIGER/Line ZCTA520 2024 (~33,791 ZIPs, public domain)
- CA: GeoNames CA_full (~899,779 postal codes, CC-BY 4.0)
- MX: GeoNames MX (~32,448 postal codes, CC-BY 4.0)
- Mock fallback: template Excel `02_Postal_Reference_MOCK` sheet supplements unmatched countries

## Gotchas
- Pipeline must run as module (`python -m src.run_pipeline`), not as script
- Reference modes: `auto`, `mock`, `parquet`, `synthetic`
- `auto` priority: `--reference` flag > default parquet > Excel mock > synthetic
- Template Excel has synthetic postal codes that don't exist in real Census data — use real client data for production
- Use `--reference-mode mock` / `make prototype` for visual demo on the full sample
- Use `--reference-mode parquet` / `make run-prod` for real client runs
- `--reference PATH` overrides reference file in `auto` or `parquet`; `--reference-sheet NAME` changes Excel mock sheet
- `data/output/lsn-map-options.html` is generated. Do not edit it by hand; edit `src/render_lsn_map_options.py`
- The supplied LSN artwork is not georeferenced GIS. The prototype uses regional anchors and canvas aggregates for branded overview; use MapLibre or GCP/georeferencing for exact lon/lat placement.
- `.local-lab/proof/lsn-map/` contains local visual proof and is gitignored
- pyrightconfig.json points to `.venv` — run `pyright` from project root

## Git Conventions
- Conventional commits
- PR required for main branch

## Plugin Usage
- Use `/code-review` before committing
- Use `/commit` for standardized commits
- Use `/feature-dev` for multi-file features
- Use `/hookify` to codify repeated mistakes into hooks

## MCP
- context7: library docs lookup
- github: PR/issue integration
- No manually configured MCP servers needed

## Onboarding Docs
- `docs/ai/claude-code-onboarding-research.md` — full audit report
- `docs/ai-prompts/` — prompt templates for pipeline and bootstrap
