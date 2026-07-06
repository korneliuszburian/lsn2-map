# AGENTS.md

> ⚠️ **PIERWSZA RZECZ po odpaleniu tego repo: przeczytaj `handoff.md` od deski do deski.**
> `handoff.md` to single source of truth dla bieżącego stanu pracy, decyzji, known-issues i instrukcji uruchomienia na nowej maszynie (venv, `make reference`, `make prototype`). Zanim cokolwiek zmienisz, zacznij tam.

## Active Task

Stan na 2026-06-30: pierwotny brief jest pokryty prototypem, a nowa paczka `NA_Map_Assets (1).zip` została rozpoznana i wpięta jako aktualny branded wariant mapy.

Ostatni czysty remote commit przed bieżącym WIP:

- `c3ef562 docs: update LSN map handoff state`

Lokalny serwer preview działał na:

- `http://127.0.0.1:8017/lsn-map-options.html` - branded prototype na nowym `NEW NA MAP.svg`, tryby `Pins`, `Regions`, `Flags`, `Heatmap`, `Heat + Pins`, fit i fullscreen.
- `http://127.0.0.1:8017/lsn-map-figma.html` - implementacja Figma node `1715:3527` (`Map Zoom-In`), dwa warianty `Default`/`Variant2` stacked, canvas map + dynamic points/clusters z CSV.
- `http://127.0.0.1:8017/lsn-map-geographic.html` - GIS-correct wariant w stylu LSN, North America Albers Equal Area.

Świeże proof screenshoty z nowego SVG są lokalnie w:

- `.local-lab/proof/lsn-map-2026-06-30/01-new-svg-pins.png`
- `.local-lab/proof/lsn-map-2026-06-30/02-new-svg-flags.png`
- `.local-lab/proof/lsn-map-2026-06-30/03-new-svg-heatmap.png`
- `.local-lab/proof/lsn-map-2026-06-30/04-new-svg-heat-pins.png`
- `.local-lab/proof/lsn-map-2026-06-30/05-figma-map-component.png`

Uwaga: w tej sesji zapis na `C:\Users\krnij\Desktop` przez `/mnt/c` zwrócił `Permission denied`, więc screenshoty proof są tylko w `.local-lab`.

Do pokazania klientowi/szefowi jako obecny branded stan używać nowego wariantu `lsn-map-options.html` z `new-na-map.svg`. Do rozmowy o precyzji współrzędnych nadal używać `lsn-map-geographic.html` jako GIS-correct proof.

`/home/krn/.codex/attachments/397a5685-3b57-4e4c-bd85-bedd091775db/pasted-text-1.txt`

Cel klienta: użyć dostarczonej mapy LSN / North America z pliku `.ai`, nanieść znaczniki z Excela, przygotować warianty do porównania:

- pinezki,
- flagi,
- heatmapa,
- heatmapa + pinezki,
- zoom,
- fullscreen na desktopie.

Klient nie ma jeszcze finalnego designu sekcji. Oczekiwany wynik to kilka sensownych propozycji, nie ciężka aplikacja ani rozbudowana architektura.

Ważne: nowy SVG jest lepszym assetem wizualnym niż stary PNG/AI, ale nadal nie zawiera CRS/projekcji/georeferencji ani semantycznych regionów. Aktualny prototyp na tym SVG może służyć jako branded overview / porównanie wariantów, ale dokładne lon/lat placement wymaga GIS basemap albo georeferencji artworku przez punkty kontrolne.

Aktualna rekomendacja do Michała / Asany: poczekać na oficjalną mapę, ale od razu doprecyzować wymagania techniczne. Jeśli klient chce exact points, mapa musi mieć znaną projekcję/georeferencję albo być przygotowana na bazie realnych danych geograficznych. Jeśli dostarczą tylko kolejny `.ai` jako ilustrację, plan B to odwzorować ich design samodzielnie na prawdziwej mapie GIS.

## Repo State Summary

Repo jest pipeline'em danych plus powtarzalny statyczny prototyp mapy klienta.

Istniejący rdzeń:

- `src/run_pipeline.py` - CLI do wczytania Excela, normalizacji, enrichu i eksportu.
- `src/clean_clients.py` - ładowanie arkusza `01_Clients_Input`.
- `src/normalize_postal.py` - normalizacja US/CA/MX.
- `src/postal_reference.py` - ładowanie referencji parquet/mock/synthetic.
- `src/render_lsn_map_options.py` - generator `data/output/lsn-map-options.html` na artworku klienta.
- `src/render_lsn_figma_map.py` - generator `data/output/lsn-map-figma.html`, implementuje Figma node `1715:3527` jako statyczny komponent z dwoma wariantami mapy.
- `src/render_lsn_geographic_map.py` - generator `data/output/lsn-map-geographic.html` z prawdziwych granic GIS w stylu LSN.
- `src/build_reference.py` - skrypt do budowy referencji z Census/GeoNames.
- `src/export.py` - eksport `clients_enriched.xlsx`, `clients_geocoded.csv`, `clients.geojson`, `geocode_exceptions.csv`, `run_summary.json`.

Istniejące assety/prototypy lokalne:

- `data/assets/client-map/north-america-map.ai` - dostarczona mapa, lokalnie rozpoznana jako PDF/AI 1 strona.
- `data/assets/client-map/north-america-map-ai.png` - 1731x1800, RGBA, 16-bit.
- `data/assets/client-map/north-america-map-ai-web.png` - 1731x1800, RGB, web-ready.
- `data/assets/client-map/new-na-map.svg` - aktualny asset z paczki `NA_Map_Assets (1).zip`, `viewBox="0 0 816 838.86"`, wektorowy i lepszy do branded preview.
- `data/assets/client-map/pin-na-map.svg` - aktualny pin z paczki, używany w trybach `Pins` i `Heat + Pins`.
- `data/assets/client-map/full-na-map.ai` - źródłowy AI z paczki `NA_Map_Assets (1).zip`, lokalnie PDF/AI.
- `data/assets/client-map/pin-na-map.ai` - źródłowy AI pina z paczki.
- `data/assets/client-map/figma-section-895-2673.png` - zrzut sekcji Figma.
- `data/assets/client-map/section-idea-1.png` - inspiracja / wariant sekcji.
- `data/output/map.html` - starszy wygenerowany MapLibre dashboard na realnej mapie geograficznej; artefakt, nie source of truth.
- `data/output/lsn-map-options.html` - generowany przez `src/render_lsn_map_options.py`; ma tryby Pins/Regions/Flags/Heatmap/Heat + Pins + fit/fullscreen.
- `data/output/lsn-map-figma.html` - generowany przez `src/render_lsn_figma_map.py`; Figma-style `Map Zoom-In` component, 804x880 overview + 804x880 zoom crop.
- `data/output/lsn-map-geographic.html` - generowany przez `src/render_lsn_geographic_map.py`; poprawny pod koordynaty, North America Albers Equal Area, tryby Exact Points/Clusters/Heatmap/Heat + Points.

Uwaga: `data/output/` jest gitignored. `lsn-map-options.html` jest artefaktem generowanym, a source of truth to `src/render_lsn_map_options.py`.

## Verified Findings

- Załącznik wymaga porównania wariantów wizualnych na mapie klienta, nie tylko standardowego GeoJSON/MapLibre dashboardu.
- Paczka `NA_Map_Assets (1).zip` zawiera `Full_NA_MAP.ai`, `NEW NA MAP.svg`, `Pin_NA_Map.ai`, `Pin_NA_Map.svg`; SVG mapy ma 740 `<path>`, 144 `<polygon>`, dwa fill style i brak CRS/projekcji/georeferencji/semantycznych ID regionów.
- Nowy renderer branded używa domyślnie `data/assets/client-map/new-na-map.svg` i `data/assets/client-map/pin-na-map.svg`; `Makefile` ma `MAP_IMAGE` i `PIN_IMAGE`.
- `make prototype` generuje pełny demo output: pipeline sample w trybie `--reference-mode mock`, potem Leaflet HTML na mapie klienta.
- `lsn-map-options.html` zawiera Leaflet, SVG/PNG map overlay, canvas piny z SVG, regionalne bubbles, exact flag markers, heatmapę, hybrid, fit i fullscreen.
- `lsn-map-figma.html` odwzorowuje Figma `Map Zoom-In`: biały komponent `844x1820`, dwa warianty `804x880`, overview i crop zoom; Figma crop ratios są zapisane w rendererze, a punkty/clustery są rysowane dynamicznie z CSV.
- `map.html` zawiera MapLibre, punkty, heatmapę, klastry i dashboard, ale używa realnego basemap zamiast mapy klienta.
- Demo pipeline w trybie `mock` generuje `1200/1200` matched, 100.0%, 0 exceptions.
- Pipeline z realnym `data/reference/postal_reference.parquet` na syntetycznym sample daje `702/1200` matched, czyli `58.5%`.
- Ten niski match-rate wynika z mieszania realnego parquetu z demo workbookiem zawierającym syntetyczne / nieistniejące kody. Nie traktować tego jako jakości finalnego klientowskiego Excela.
- Workbook `data/sample/north_america_generator_mapping_template.xlsx` ma mockowy arkusz `02_Postal_Reference_MOCK`, który w samym workbooku daje 1200/1200 matched.
- Testy pokrywają jawny tryb referencji `auto/mock/parquet/synthetic`.
- Figma node `895:2673` z pliku `4NrYxpTRMC0mAtyuZMVXMK` został sprawdzony przez Figma MCP. To pełny homepage mock z sekcją "Our Reach Across North America" i statyczną mapą, nie gotowa specyfikacja interaktywnej mapy.
- Browser proof po poprawce rendereru exact: `.local-lab/proof/lsn-map/runtime-proof-exact-points.txt` pokazuje `active=Exact Points`, `rows=1200`, `plotted=1200`, `renderer=canvas-exact-points-and-region-aggregates`, `pointPlacement.lonLatLinear=1200`, `pointPlacement.clamped=0`, `markerIcons=0`.
- Browser proof GIS: `.local-lab/proof/lsn-map/runtime-proof-geographic.txt` pokazuje `active=Exact Points`, `rows=1200`, `plotted=1200`, `insideViewport=1200`, `rawInsideBasemap=1019`, `displayAdjusted=181`, `markerIcons=0`, `pointCanvas=1`, `zoomAnimation=false`.
- Browser proof nowego SVG z 2026-06-30: runtime eval pokazał `rows=1200`, `plotted=1200`, `sourceMap=data/assets/client-map/new-na-map.svg`, `sourcePin=data/assets/client-map/pin-na-map.svg`, `renderer=svg-map-canvas-pins-and-region-aggregates`, `markerIcons=0`, `markerCanvas=1`, `pinSvg=true`, `zoomAnimation=false`.
- Proof screenshoty nowego SVG z 2026-06-30: `.local-lab/proof/lsn-map-2026-06-30/01-new-svg-pins.png`, `02-new-svg-flags.png`, `03-new-svg-heatmap.png`, `04-new-svg-heat-pins.png`. `02-new-svg-flags.png`, `03-new-svg-heatmap.png`, `04-new-svg-heat-pins.png` były obejrzane przez `view_image`.
- Browser proof Figma map z 2026-06-30: runtime eval pokazał `figmaNode=1715:3527`, `variants=["overview","zoom"]`, `rows=1200`, `plotted=1200`, `clusters=38`, `renderer=figma-map-zoom-in-canvas`. Screenshot `05-figma-map-component.png` był obejrzany przez `view_image`.
- Screenshoty do Asany bez badge'y z 2026-06-19 są w `C:\Users\krnij\Desktop\lsn-map-screenshots\exact-points-only\`: `01-artwork-exact-points.png` i `02-gis-exact-points.png`.
- Aktualne screenshoty z 2026-06-22 są w `C:\Users\krnij\Desktop\lsn-map-current-state-2026-06-22\`: `01-artwork-exact-points.png` i `02-gis-exact-points.png`.
- Screenshoty proof: `.local-lab/proof/lsn-map/regions-bubbles-1920x1080.png`, `region-badges-1920x1080.png`, `heat-regions-1920x1080.png`, `hybrid-regions-1920x1080.png`, `regions-bubbles-1440x900.png`.
- Finalne gate'y: `make test` 36 passed, `make lint` all checks passed, `make prototype` passed, `make typecheck` failuje 16 błędami pyright/pandas typing jako zapisany residual risk.
- Gate'y tej sesji 2026-06-30: `python3 -m py_compile src/render_lsn_map_options.py src/render_lsn_figma_map.py` passed; `python3 -m src.render_lsn_map_options --input data/output/clients_geocoded.csv --map-image data/assets/client-map/new-na-map.svg --pin-image data/assets/client-map/pin-na-map.svg --output data/output/lsn-map-options.html` passed; `make map-options` passed; `make map-figma` passed. Pełne `make prototype/test/lint` nie było uruchomione, bo lokalne `.venv` nie istnieje w tej sesji, a globalny Python nie ma `pandas`.

## Current Worktree Notes

Stan bieżącego WIP 2026-06-30:

- `main` był czysty i równy z `origin/main` na commitcie `c3ef562` przed wpięciem nowej paczki assetów.
- Source changes do commita: `Makefile`, `src/render_lsn_map_options.py`, `src/render_lsn_figma_map.py`, `AGENTS.md`, `GOAL.md`, `README.md`, `docs/lsn-map-state-and-plan-2026-06-19.md`, `.gitignore`.
- Nowe assety source do commita: `data/assets/client-map/new-na-map.svg`, `pin-na-map.svg`, `full-na-map.ai`, `pin-na-map.ai`.
- Nie commitować rootowego `NA_Map_Assets (1).zip`; to dostarczony załącznik i powinien być ignorowany przez `.gitignore`.
- `data/output/*` pozostaje generated i gitignored.
- `.local-lab/*` pozostaje lokalnym proof/scratch i gitignored.
- `data/reference/postal_reference.parquet` oraz zipy Natural Earth pozostają lokalnym cache/build artifactem i są ignorowane.
- Screeny na Desktop nie są częścią repo; w tej sesji zapis przez `/mnt/c` był zablokowany.

Nie revertować istniejących zmian bez wyraźnej zgody użytkownika. Traktować commit `c3ef562` plus bieżący WIP jako aktualny kontekst pracy.

## Recommended Direction

Najlepszy praktyczny kierunek na teraz:

1. Utrzymywać `src/render_lsn_map_options.py` jako source of truth dla prototypu `lsn-map-options.html`.
2. Zostawić pierwszą wersję jako statyczny HTML bez npm/build step, bo klient potrzebuje porównania koncepcji.
3. Dla mapy klienta użyć Leaflet z `CRS.Simple` / image overlay, bo mapa `.ai`/`.svg` nie jest prawdziwą projekcją GIS.
4. Traktować pozycje na artworku jako regionalne agregaty, dobre do koncepcji, ale nie do geodezyjnej precyzji.
5. Równolegle zachować MapLibre jako wariant "real geography", jeśli klient uzna, że interaktywny basemap jest ważniejszy niż ich ilustracyjna mapa.
6. Używać `lsn-map-geographic.html` jako kierunku dla exact deployment points; obecny design można dopolerować przez generalizację, crop/inset Alaska/Canada islands i klastering.
7. Nie budować od razu WordPressowego bloku ani React appki. Najpierw client-review HTML + screenshoty/proof.
8. Jeżeli klient chce dokładne punkty na ich brandowanej mapie, poprosić o georeferencję/CRS/control points albo przygotować własną mapę GIS w ich stylu.

## Concrete Next Steps

1. Dokończyć docs/cleanup tego WIP, potem commit i push, jeśli użytkownik poprosi.
2. Pokazać aktualny branded preview na `http://127.0.0.1:8017/lsn-map-options.html`.
3. W odpowiedzi do klienta powiedzieć: wszystkie warianty z briefu są możliwe i obecnie działają w demo, ale exact lon/lat na ich SVG/AI wymaga georeferencji albo mapy GIS w ich stylu.
4. Jeśli trzeba wysłać screeny, użyć `.local-lab/proof/lsn-map-2026-06-30/*` albo wygenerować świeże przez agent-browser.
5. Dopiero po wyborze kierunku planować WordPress/React/embed.
6. Opcjonalna techniczna poprawka przed PR: posprzątać pyright pandas/GeoPandas typing, jeśli ma być twardym gate'em.

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

Renderer mapy klienta można sprawdzić bez pandas, jeśli `data/output/clients_geocoded.csv` już istnieje:

```bash
python3 -m src.render_lsn_map_options \
  --input data/output/clients_geocoded.csv \
  --map-image data/assets/client-map/new-na-map.svg \
  --pin-image data/assets/client-map/pin-na-map.svg \
  --output data/output/lsn-map-options.html
```

Figma-style renderer:

```bash
make map-figma
```

## Guardrails

- Nie commitować realnych danych klienta.
- Nie commitować dużych generated outputów z `data/output/`, chyba że użytkownik wyraźnie wybierze taki artefakt jako deliverable.
- Nie traktować `data/output/map.html` jako źródła prawdy.
- Nie edytować ręcznie `data/output/lsn-map-options.html`; generować go przez `make prototype` albo `make map-options`.
- Nie twierdzić, że geokodowanie produkcyjne jest gotowe na 98% bez uruchomienia na prawdziwym Excelu klienta.
- Nie overengineerować: najbliższy deliverable to porównywalny, klikalny prototyp + plan, nie platforma mapowa.
