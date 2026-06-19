# AGENTS.md

## Active Task

Stan na 2026-06-19: prototyp porównawczy LSN map jest zbudowany i zweryfikowany; po feedbacku renderer ma osobny tryb `Exact Points` oraz regionalne agregaty canvas zamiast 1200 markerów DOM.

`/home/krn/.codex/attachments/397a5685-3b57-4e4c-bd85-bedd091775db/pasted-text-1.txt`

Cel klienta: użyć dostarczonej mapy LSN / North America z pliku `.ai`, nanieść znaczniki z Excela, przygotować warianty do porównania:

- pinezki,
- flagi,
- heatmapa,
- heatmapa + pinezki,
- zoom,
- fullscreen na desktopie.

Klient nie ma jeszcze finalnego designu sekcji. Oczekiwany wynik to kilka sensownych propozycji, nie ciężka aplikacja ani rozbudowana architektura.

Ważne: dostarczony artwork nie jest georeferencjonowaną mapą GIS. Aktualny prototyp na tym artworku jest branded regional overview. Dokładne lon/lat placement wymaga MapLibre/real geography albo georeferencji artworku przez punkty kontrolne.

## Repo State Summary

Repo jest pipeline'em danych plus powtarzalny statyczny prototyp mapy klienta.

Istniejący rdzeń:

- `src/run_pipeline.py` - CLI do wczytania Excela, normalizacji, enrichu i eksportu.
- `src/clean_clients.py` - ładowanie arkusza `01_Clients_Input`.
- `src/normalize_postal.py` - normalizacja US/CA/MX.
- `src/postal_reference.py` - ładowanie referencji parquet/mock/synthetic.
- `src/render_lsn_map_options.py` - generator `data/output/lsn-map-options.html` na artworku klienta.
- `src/render_lsn_geographic_map.py` - generator `data/output/lsn-map-geographic.html` z prawdziwych granic GIS w stylu LSN.
- `src/build_reference.py` - nieśledzony jeszcze plik do budowy referencji z Census/GeoNames.
- `src/export.py` - eksport `clients_enriched.xlsx`, `clients_geocoded.csv`, `clients.geojson`, `geocode_exceptions.csv`, `run_summary.json`.

Istniejące assety/prototypy lokalne:

- `data/assets/client-map/north-america-map.ai` - dostarczona mapa, lokalnie rozpoznana jako PDF/AI 1 strona.
- `data/assets/client-map/north-america-map-ai.png` - 1731x1800, RGBA, 16-bit.
- `data/assets/client-map/north-america-map-ai-web.png` - 1731x1800, RGB, web-ready.
- `data/assets/client-map/figma-section-895-2673.png` - zrzut sekcji Figma.
- `data/assets/client-map/section-idea-1.png` - inspiracja / wariant sekcji.
- `data/output/map.html` - starszy wygenerowany MapLibre dashboard na realnej mapie geograficznej; artefakt, nie source of truth.
- `data/output/lsn-map-options.html` - generowany przez `src/render_lsn_map_options.py`; ma tryby Exact Points/Regions/Badges/Heatmap/Heat + Points + fit/fullscreen.
- `data/output/lsn-map-geographic.html` - generowany przez `src/render_lsn_geographic_map.py`; poprawny pod koordynaty, North America Albers Equal Area, tryby Exact Points/Clusters/Heatmap/Heat + Points.

Uwaga: `data/output/` jest gitignored. `lsn-map-options.html` jest artefaktem generowanym, a source of truth to `src/render_lsn_map_options.py`.

## Verified Findings

- Załącznik wymaga porównania wariantów wizualnych na mapie klienta, nie tylko standardowego GeoJSON/MapLibre dashboardu.
- `make prototype` generuje pełny demo output: pipeline sample w trybie `--reference-mode mock`, potem Leaflet HTML na mapie klienta.
- `lsn-map-options.html` zawiera Leaflet, obraz mapy jako overlay, regionalne bubbles, badges, heatmapę, hybrid, fit i fullscreen.
- `map.html` zawiera MapLibre, punkty, heatmapę, klastry i dashboard, ale używa realnego basemap zamiast mapy klienta.
- Demo pipeline w trybie `mock` generuje `1200/1200` matched, 100.0%, 0 exceptions.
- Pipeline z realnym `data/reference/postal_reference.parquet` na syntetycznym sample daje `702/1200` matched, czyli `58.5%`.
- Ten niski match-rate wynika z mieszania realnego parquetu z demo workbookiem zawierającym syntetyczne / nieistniejące kody. Nie traktować tego jako jakości finalnego klientowskiego Excela.
- Workbook `data/sample/north_america_generator_mapping_template.xlsx` ma mockowy arkusz `02_Postal_Reference_MOCK`, który w samym workbooku daje 1200/1200 matched.
- Testy pokrywają jawny tryb referencji `auto/mock/parquet/synthetic`.
- Figma node `895:2673` z pliku `4NrYxpTRMC0mAtyuZMVXMK` został sprawdzony przez Figma MCP. To pełny homepage mock z sekcją "Our Reach Across North America" i statyczną mapą, nie gotowa specyfikacja interaktywnej mapy.
- Browser proof po poprawce rendereru exact: `.local-lab/proof/lsn-map/runtime-proof-exact-points.txt` pokazuje `active=Exact Points`, `rows=1200`, `plotted=1200`, `renderer=canvas-exact-points-and-region-aggregates`, `pointPlacement.lonLatLinear=1200`, `pointPlacement.clamped=0`, `markerIcons=0`.
- Browser proof GIS: `.local-lab/proof/lsn-map/runtime-proof-geographic.txt` pokazuje `active=Exact Points`, `rows=1200`, `plotted=1200`, `insideViewport=1200`, `rawInsideBasemap=1019`, `displayAdjusted=181`, `markerIcons=0`, `pointCanvas=1`, `zoomAnimation=false`.
- Aktualne screenshoty do Asany bez badge'y są w `C:\Users\krnij\Desktop\lsn-map-screenshots\exact-points-only\`: `01-artwork-exact-points.png` i `02-gis-exact-points.png`.
- Screenshoty proof: `.local-lab/proof/lsn-map/regions-bubbles-1920x1080.png`, `region-badges-1920x1080.png`, `heat-regions-1920x1080.png`, `hybrid-regions-1920x1080.png`, `regions-bubbles-1440x900.png`.
- Finalne gate'y: `make test` 36 passed, `make lint` all checks passed, `make prototype` passed, `make typecheck` failuje 16 błędami pyright/pandas typing jako zapisany residual risk.

## Current Worktree Notes

Aktualny status jest celowo dirty, bo praca nie była commitowana w tej sesji. Decyzje:

- zmodyfikowane source/config/docs: `.gitignore`, `CLAUDE.md`, `Makefile`, `README.md`, `requirements.txt`, `src/postal_reference.py`, `src/run_pipeline.py`, `tests/test_pipeline.py`;
- nowe source/docs: `AGENTS.md`, `GOAL.md`, `docs/lsn-map-state-and-plan-2026-06-19.md`, `src/build_reference.py`, `src/render_lsn_map_options.py`, `docs/ai-prompts/map_visualization_prompt.md`;
- source assety demo: `data/assets/client-map/*`;
- placeholder: `data/reference/.gitkeep` może zostać jako commit candidate, a `data/reference/postal_reference.parquet` zostaje ignorowanym lokalnym build artifactem;
- generated/ignored: `data/output/*`, `.local-lab/proof/lsn-map/*`, cache/bytecode.

Nie revertować tych zmian bez wyraźnej zgody użytkownika. Traktować je jako aktualny kontekst pracy.

## Recommended Direction

Najlepszy praktyczny kierunek na teraz:

1. Utrzymywać `src/render_lsn_map_options.py` jako source of truth dla prototypu `lsn-map-options.html`.
2. Zostawić pierwszą wersję jako statyczny HTML bez npm/build step, bo klient potrzebuje porównania koncepcji.
3. Dla mapy klienta użyć Leaflet z `CRS.Simple` / image overlay, bo mapa `.ai` nie jest prawdziwą projekcją GIS.
4. Traktować pozycje na artworku jako regionalne agregaty, dobre do koncepcji, ale nie do geodezyjnej precyzji.
5. Równolegle zachować MapLibre jako wariant "real geography", jeśli klient uzna, że interaktywny basemap jest ważniejszy niż ich ilustracyjna mapa.
6. Używać `lsn-map-geographic.html` jako kierunku dla exact deployment points; obecny design można dopolerować przez generalizację, crop/inset Alaska/Canada islands i klastering.
7. Nie budować od razu WordPressowego bloku ani React appki. Najpierw client-review HTML + screenshoty/proof.

## Concrete Next Steps

1. Pokazać użytkownikowi/klientowi lokalny prototyp: `http://127.0.0.1:8017/lsn-map-options.html`.
2. Zebrać decyzję: Exact Points, Regions, Badges, Heatmap, Heat + Points, albo GIS/GCP real geography.
3. Dopiero po wyborze kierunku planować WordPress/React/embed.
4. Opcjonalna techniczna poprawka przed PR: posprzątać pyright pandas/GeoPandas typing, jeśli ma być twardym gate'em.

## Commands

Używać lokalnego venv:

```bash
source .venv/bin/activate
make prototype
make prototype-geographic
make test
make lint
make typecheck  # known pyright residual risk: 16 pandas/GeoPandas typing errors
```

Globalne `python3` w tym środowisku nie ma `pandas`; do wiarygodnych uruchomień używać `.venv/bin/python`.

## Guardrails

- Nie commitować realnych danych klienta.
- Nie commitować dużych generated outputów z `data/output/`, chyba że użytkownik wyraźnie wybierze taki artefakt jako deliverable.
- Nie traktować `data/output/map.html` jako źródła prawdy.
- Nie edytować ręcznie `data/output/lsn-map-options.html`; generować go przez `make prototype` albo `make map-options`.
- Nie twierdzić, że geokodowanie produkcyjne jest gotowe na 98% bez uruchomienia na prawdziwym Excelu klienta.
- Nie overengineerować: najbliższy deliverable to porównywalny, klikalny prototyp + plan, nie platforma mapowa.
