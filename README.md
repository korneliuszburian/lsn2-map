# LSN North America Map Pipeline

Pipeline geokoduje deploymenty generatorów z Excela dla US/CA/MX i eksportuje dane map-ready: XLSX, CSV, GeoJSON, exceptions CSV oraz run summary.

Aktualny cel repo jest szerszy niż sam pipeline: przygotować powtarzalny prototyp mapy klienta LSN/North America z wariantami Pins, Regions, Flags, Heatmap i Heat + Pins. Szczegóły wykonawcze są w `GOAL.md` i `docs/lsn-map-state-and-plan-2026-06-19.md`.

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
make prototype-geographic # demo pipeline + GIS-correct styled map HTML
make map-final          # GIS-correct final-style HTML (light basemap + hot-zones + points)
make run-demo           # sample workbook with mock reference, 1200/1200 demo rows
make run-parquet-sample # sample workbook with real local parquet, expected low demo match
make run-prod           # CLIENT_INPUT=data/input/clients.xlsx with parquet reference
make map-options        # render data/output/lsn-map-options.html from clients_geocoded.csv
make map-figma          # render data/output/lsn-map-figma.html matching Figma Map Zoom-In node
make map-geographic     # render data/output/lsn-map-geographic.html from clients_geocoded.csv
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
python -m src.render_lsn_map_options \
  --input data/output/clients_geocoded.csv \
  --map-image data/assets/client-map/new-na-map.svg \
  --pin-image data/assets/client-map/pin-na-map.svg \
  --output data/output/lsn-map-options.html
python -m src.render_lsn_figma_map \
  --input data/output/clients_geocoded.csv \
  --map-image data/assets/client-map/new-na-map.svg \
  --output data/output/lsn-map-figma.html
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
- `lsn-map-options.html`
- `lsn-map-figma.html`
- `lsn-map-geographic.html`
- `lsn-map-final.html`
- `lsn-north-america-geographic.svg`
- `lsn-north-america-final.svg`

`data/output/` is ignored. Regenerate the map prototype with `make prototype`; the source of truth is `src/render_lsn_map_options.py`.

The supplied LSN artwork is not a georeferenced GIS basemap. The current renderer supports SVG/PNG image overlays, canvas pins, regional bubbles, exact flag markers, heatmap and heat+pins views. It uses deterministic regional anchors for branded overview performance. Use the GIS-correct prototype, or georeference the artwork with control points, for trustworthy exact lon/lat placement.

The Figma-aligned prototype is `data/output/lsn-map-figma.html`. It implements Figma node `1715:3527` (`Map Zoom-In`) as two stacked `804x880` variants: overview and zoom crop. It keeps the Figma crop ratios, but draws points and cluster circles dynamically from `clients_geocoded.csv` instead of baking them into an image.

The GIS-correct prototype is `data/output/lsn-map-geographic.html`. It generates an LSN-styled SVG basemap from Natural Earth boundaries using North America Albers Equal Area projection, then projects deployment lon/lat into the same coordinate space.

The final visual variant is `data/output/lsn-map-final.html`. It keeps GIS projection correctness, but applies a light neutral land style, white boundaries, small green points, and green hot-zones with dashed outlines (`Points`/`Hot-zones`/`Pins`/`Flags` modes). It is intended as the main client-facing review candidate.

Local preview URL after `make serve`:

```text
http://127.0.0.1:8017/lsn-map-options.html
http://127.0.0.1:8017/lsn-map-figma.html
http://127.0.0.1:8017/lsn-map-final.html
```

## Client Map Assets

Client/demo assets live under `data/assets/client-map/`.

Key files:

- `north-america-map.ai` - original supplied AI/PDF artwork.
- `north-america-map-ai-web.png` - browser-ready map artwork.
- `new-na-map.svg` - current vector North America artwork from `NA_Map_Assets (1).zip`; default for `make map-options`.
- `pin-na-map.svg` - current pin SVG from `NA_Map_Assets (1).zip`; default pin marker.
- `full-na-map.ai` - source AI/PDF from the new asset zip.
- `pin-na-map.ai` - source pin AI/PDF from the new asset zip.
- `figma-section-895-2673.png` - Figma section screenshot context.

## Current Known State

- Last full gate before the 2026-06-30 asset update: `pytest` passing and `ruff` passing.
- 2026-06-30 asset update gate: standalone `src.render_lsn_map_options`, `src.render_lsn_figma_map`, `make map-options`, and `make map-figma` passing with `new-na-map.svg`.
- `pyright`: currently failing on pandas/GeoPandas typing issues.
- Last full `make prototype`: passing; after 2026-06-30 asset update, only the standalone renderer was rerun.
- Map renderer: canvas pins plus regional aggregates, not 1200 DOM markers.
- Visual proof is local under `.local-lab/proof/lsn-map/` and `.local-lab/proof/lsn-map-2026-06-30/` and is ignored by git.

2026-06-30 note: in the current shell session `.venv` was absent, so only the standalone renderer was verified with global `python3`. Recreate/activate `.venv` before running full pipeline/test/lint gates.

## Guardrails

- Do not commit real client input data.
- Do not commit large generated references or random `data/output` artifacts.
- Do not claim production geocode quality without running on the real client workbook.
- Do not build a WordPress block or React app until the client chooses a direction.
