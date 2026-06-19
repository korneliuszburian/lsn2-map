# LSN North America Map Pipeline

Pipeline geokoduje deploymenty generatorów z Excela dla US/CA/MX i eksportuje dane map-ready: XLSX, CSV, GeoJSON, exceptions CSV oraz run summary.

Aktualny cel repo jest szerszy niż sam pipeline: przygotować powtarzalny prototyp mapy klienta LSN/North America z wariantami Exact Points, Regions, Badges, Heatmap i Heat + Points. Szczegóły wykonawcze są w `GOAL.md` i `docs/lsn-map-state-and-plan-2026-06-19.md`.

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
make run-demo           # sample workbook with mock reference, 1200/1200 demo rows
make run-parquet-sample # sample workbook with real local parquet, expected low demo match
make run-prod           # CLIENT_INPUT=data/input/clients.xlsx with parquet reference
make map-options        # render data/output/lsn-map-options.html from clients_geocoded.csv
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
  --map-image data/assets/client-map/north-america-map-ai-web.png \
  --output data/output/lsn-map-options.html
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
- `lsn-map-geographic.html`
- `lsn-north-america-geographic.svg`

`data/output/` is ignored. Regenerate the map prototype with `make prototype`; the source of truth is `src/render_lsn_map_options.py`.

The supplied LSN artwork is not a georeferenced GIS basemap. The current renderer supports Exact Points as a diagnostic lon/lat-to-image view, plus deterministic regional anchors for branded overview performance. Use the GIS-correct prototype, or georeference the artwork with control points, for trustworthy exact lon/lat placement.

The GIS-correct prototype is `data/output/lsn-map-geographic.html`. It generates a new LSN-styled SVG basemap from Natural Earth boundaries using North America Albers Equal Area projection, then projects deployment lon/lat into the same coordinate space. Demo data currently has 181 raw outside/coastal records that are display-snapped and counted in runtime proof as `displayAdjusted`.

Local preview URL after `make serve`:

```text
http://127.0.0.1:8017/lsn-map-options.html
```

## Client Map Assets

Client/demo assets live under `data/assets/client-map/`.

Key files:

- `north-america-map.ai` - original supplied AI/PDF artwork.
- `north-america-map-ai-web.png` - browser-ready map artwork.
- `figma-section-895-2673.png` - Figma section screenshot context.

## Current Known State

- `pytest`: passing.
- `ruff`: passing.
- `pyright`: currently failing on pandas/GeoPandas typing issues.
- `make prototype`: passing; generates the demo pipeline output and `data/output/lsn-map-options.html`.
- Map renderer: canvas exact points plus regional aggregates, not 1200 DOM markers.
- Visual proof is local under `.local-lab/proof/lsn-map/` and is ignored by git.

## Guardrails

- Do not commit real client input data.
- Do not commit large generated references or random `data/output` artifacts.
- Do not claim production geocode quality without running on the real client workbook.
- Do not build a WordPress block or React app until the client chooses a direction.
