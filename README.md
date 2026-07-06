# LSN North America Map Pipeline

Pipeline geokoduje deploymenty generatorów z Excela dla US/CA/MX i eksportuje dane map-ready: XLSX, CSV, GeoJSON, exceptions CSV oraz run summary.

Aktualny klient-facing deliverable to jedna finalna mapa LSN/North America: jasna GIS/canvas mapa + zielone hot-zones + animowane piny + Points toggle + smooth zoom/fullscreen. Starsze warianty porównawcze nie są już aktywną ścieżką review.

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Używaj `.venv`. Globalne `python3` w aktualnym środowisku nie ma kompletu zależności takich jak `pandas`.

## Commands

```bash
make prototype          # demo pipeline + client-map HTML
make map-final          # final client-facing HTML (GIS/canvas map + hot-zones + pins)
make run-demo           # sample workbook with mock reference, 1200/1200 demo rows
make run-parquet-sample # sample workbook with real local parquet, expected low demo match
make run-prod           # CLIENT_INPUT=data/input/clients.xlsx with parquet reference
make serve              # serve data/output at http://127.0.0.1:8017/
make preview            # regenerate prototype, then serve it in the foreground
make test               # pytest
make lint               # ruff
make typecheck          # pyright, currently has known pandas/GeoPandas typing failures
make clean              # remove data/output
```

Direct run:

```bash
python -m src.run_pipeline \
  --input data/sample/north_america_generator_mapping_template.xlsx \
  --output data/output \
  --reference-mode mock
python -m src.render_lsn_final_map \
  --input data/output/clients_geocoded.csv \
  --output data/output/lsn-map-final.html \
  --basemap-output data/output/lsn-north-america-final.svg \
  --pin-image data/assets/client-map/pin-na-map.svg
```

Build local postal reference:

```bash
make reference
```

`data/reference/postal_reference.parquet` is a local generated artifact and is ignored by git.

## Reference Behavior

The pipeline has explicit reference modes:

- `auto`: explicit `--reference`, default parquet, Excel mock, then synthetic fallback.
- `mock`: force workbook sheet `02_Postal_Reference_MOCK`; use for visual demo/prototype.
- `parquet`: force explicit/default parquet; use for client/production data.
- `synthetic`: generate deterministic dev-only coordinates from input rows.

Important: the sample workbook contains synthetic postal codes. Demo mode (`--reference-mode mock`) produces `1200/1200` matched rows for visual comparison. Parquet mode on the same synthetic sample currently produces `702/1200` matched rows and correctly warns below the 98% target.

## Output Files

Generated under `data/output/`:

- `clients_enriched.xlsx`
- `clients_geocoded.csv`
- `clients.geojson`
- `geocode_exceptions.csv`
- `run_summary.json`
- `lsn-map-final.html`

`data/output/` is ignored. Regenerate the final map with `make prototype` or `make map-final`; the source of truth is `src/render_lsn_final_map.py`.

The supplied LSN artwork is not a georeferenced GIS basemap. The active final renderer therefore uses a GIS-correct generated basemap styled to match the client reference, with Great Lakes cutouts, Caribbean visual islands, a Hawaii inset when relevant, canvas hot-zones, animated SVG pins, Points/Pins/Hot Zones controls, and smooth zoom.

Local preview URL after `make serve`:

```text
http://127.0.0.1:8017/lsn-map-final.html
```

## Client Map Assets

Client/demo assets live under `data/assets/client-map/`.

Key files:

- `north-america-map.ai` - original supplied AI/PDF artwork.
- `north-america-map-ai-web.png` - browser-ready map artwork.
- `new-na-map.svg` - client vector reference artwork, used as visual/design reference.
- `pin-na-map.svg` - current pin SVG from `NA_Map_Assets (1).zip`; default pin marker.
- `full-na-map.ai` - source AI/PDF from the new asset zip.
- `pin-na-map.ai` - source pin AI/PDF from the new asset zip.
- `figma-section-895-2673.png` - Figma section screenshot context.

## Current Known State

- Last full gate before the 2026-06-30 asset update: `pytest` passing and `ruff` passing.
- 2026-07-06 final-map reset: active client-facing output is only `data/output/lsn-map-final.html`, generated from `src.render_lsn_final_map`.
- `pyright`: currently failing on pandas/GeoPandas typing issues.
- Map renderer: one canvas overlay with green hot-zones plus SVG pins, not 1200 DOM markers.
- Visual proof is local under `.local-lab/proof/lsn-map/` and `.local-lab/proof/lsn-map-2026-06-30/` and is ignored by git.

2026-06-30 note: in the current shell session `.venv` was absent, so only the standalone renderer was verified with global `python3`. Recreate/activate `.venv` before running full pipeline/test/lint gates.

## Guardrails

- Do not commit real client input data.
- Do not commit large generated references or random `data/output` artifacts.
- Do not claim production geocode quality without running on the real client workbook.
- Do not build a WordPress block or React app until the client chooses a direction.
