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

- Run pipeline: `python -m src.run_pipeline --input data/input/clients.xlsx --output data/output`
- Run with sample: `make run`
- Tests: `make test` or `python -m pytest tests/ -v`
- Lint: `make lint` or `ruff check src/ tests/`
- Typecheck: `pyright src/ tests/`
- Clean outputs: `make clean`

## Architecture
- `src/run_pipeline.py` — CLI entry point (run as `python -m src.run_pipeline`)
- `src/clean_clients.py` — load Excel + normalize countries/postals
- `src/normalize_postal.py` — US/CA/MX postal-code normalization
- `src/postal_reference.py` — load mock or production geocode reference
- `src/enrich.py` — left-join clients to reference by geo_key
- `src/qa.py` — quality checks (bounds, duplicates, missing fields)
- `src/export.py` — XLSX/CSV/GeoJSON/JSON export
- `data/input/` — raw Excel files (gitignored)
- `data/output/` — generated outputs (gitignored)
- `data/sample/` — template files (committed)
- `tests/` — 33 tests (25 unit + 8 integration)

## Data Rules
- Never commit real client data
- Treat postal_code_raw as text (preserve leading zeros)
- geo_key = country_code + "|" + postal_code_norm
- Target: 98%+ match rate for valid postal codes
- Coordinate bounds: US lat 18..72 lon -180..-60; CA lat 41..84 lon -142..-50; MX lat 14..33 lon -119..-86

## Gotchas
- Pipeline must run as module (`python -m src.run_pipeline`), not as script
- Postal reference comes from `02_Postal_Reference_MOCK` sheet in the same Excel workbook
- `--reference-sheet` flag changes the reference sheet name
- Mock reference only — production needs Census ZCTA5 / StatCan PCCF / SEPOMEX
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
