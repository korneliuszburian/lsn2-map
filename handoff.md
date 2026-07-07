# Handoff — LSN2 Map (North America Generator Deployment Mapping)

> **Pierwsza rzecz po odpaleniu repo: przeczytaj ten plik (`handoff.md`) od deski do deski.**
> To jest single source of truth dla bieżącego stanu pracy, decyzji, known-issues i tego, jak uruchomić projekt na nowej maszynie.
> Datum ostatniej aktualizacji: **2026-07-07**.

---

## 0. TL;DR dla nowej maszyny

Po `git clone` na nowym PC trzeba wykonać **dokładnie te kroki**, żeby być z powrotem w pracy:

```bash
git clone https://github.com/korneliuszburian/lsn2-map.git
cd lsn2-map

# 1) venv + deps
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# 2) zbuduj referencję geokodowania (jedyna rzecz, której nie trzymamy w git; ~2 min, ~504 MB pobierania)
make reference

# 3) test smoke — demo pipeline, oczekiwane 1200/1200 matched
make run-demo

# 4) wygenerować finalną mapę review:
make map-final
make prototype

# 5) podgląd w przeglądarce
make serve   # http://127.0.0.1:8017/lsn-map-final.html
```

Aktualny check list dla tej tury:
- `make map-final` ✅
- `python -m py_compile src/render_lsn_final_map.py` ✅
- `make test` ✅ (`51 passed`)
- `make lint` ✅
- `make typecheck` ❌ (brak `pyright` w lokalnym PATH)

Wygenerowane artefakty (do odtworzenia / nie commitujemy):
- `data/output/lsn-map-final.html`
- `data/output/lsn-north-america-final.svg`
- `data/output/lsn-north-america-final-short.svg`
- `data/output/lsn-north-america-final-hawaii.svg`
- `data/output/clients_geocoded.csv`

Wszystkie source'y, assety artworku i kod rendererów **są w repo** — niczego nie trzeba dogrywać ręcznie.
Jedyny nie-commitowany element to `data/reference/postal_reference.parquet` (build artifact, gitignored) → przebudowywany przez `make reference`.

---

## 1. Cel projektu

Zgeokodować ~1200 wdrożeń generatorów na terenie US/CA/MX z Excela wejściowego i wyprodukować:
- wzbogacony Excel (`clients_enriched.xlsx`),
- CSV (`clients_geocoded.csv`),
- GeoJSON EPSG:4326 (`clients.geojson`),
- raporty QA (`geocode_exceptions.csv`),
- podsumowanie uruchomienia (`run_summary.json`),
- oraz **statyczną finalną mapę HTML klienta** (jasna mapa GIS/canvas + pinezki + zielone hot-zones + zoom / fullscreen).

Klient (LSN) nie ma jeszcze finalnego designu sekcji mapy. Oczekiwany deliverable to **kilka sensownych propozycji**, nie ciężka aplikacja ani rozbudowana architektura.

---

## 2. Stack i komendy

- Python 3.12, venv wymagany (`source .venv/bin/activate` przed wszystkim).
- Pakiety: `pandas`, `geopandas`, `shapely`, `pyarrow`, `openpyxl`, `requests`, `pytest`, `ruff`, `pyright` (patrz `requirements.txt`).
- Globalny `python3` na tej maszynie **nie ma pandas** → zawsze używać `.venv/bin/python`.

Kluczowe targety Makefile:

| Target | Co robi |
|---|---|
| `make reference` | Buduje `data/reference/postal_reference.parquet` z Census/GeoNames (~2 min, ~504 MB) |
| `make run-demo` | Pipeline na sample z `--reference-mode mock` → oczekiwane **1200/1200** |
| `make run-prod` | Pipeline na `CLIENT_INPUT=data/input/clients.xlsx` z realnym parquet |
| `make map-final` | Render `lsn-map-final.html` (jedyna aktywna client-facing mapa: final GIS/canvas + hot-zones + pins) |
| `make prototype` | `run-demo` + `map-final` |
| `make serve` | Lokalny HTTP na `http://127.0.0.1:8017/` podający `data/output/` |
| `make test` / `lint` / `typecheck` | pytest (36 testów) / ruff / pyright |

Pipeline **musi** być uruchamiany jako moduł: `python -m src.run_pipeline` (nie jako skrypt).

---

## 3. Architektura (source of truth)

- `src/run_pipeline.py` — CLI entry point (`python -m src.run_pipeline`)
- `src/build_reference.py` — pobiera realne źródła geokodowania, buduje parquet
- `src/clean_clients.py` — ładuje Excel, normalizuje kraje/kody pocztowe (arkusz `01_Clients_Input`)
- `src/normalize_postal.py` — normalizacja US/CA/MX
- `src/postal_reference.py` — ładuje referencję parquet/mock/synthetic
- `src/enrich.py` — left-join klientów do referencji po `geo_key`
- `src/qa.py` — checki (bounds, duplikaty, brakujące pola)
- `src/export.py` — eksport XLSX/CSV/GeoJSON/JSON
- `src/render_lsn_final_map.py` — **source of truth** dla `lsn-map-final.html` (finalny client-facing renderer)
- `src/render_lsn_map_options.py` — historyczny artwork renderer, nieaktywna ścieżka review
- `src/render_lsn_figma_map.py` — historyczny renderer Figma, nieaktywna ścieżka review
- `src/render_lsn_geographic_map.py` — historyczny GIS proof, nieaktywna ścieżka review

Tryby referencji: `auto`, `mock`, `parquet`, `synthetic`. Priorytet `auto`: `--reference` > domyślny parquet > Excel mock > synthetic.

### Asset artworku (`data/assets/client-map/`)
- `new-na-map.svg` — aktualny branded asset (z paczki `NA_Map_Assets`), `viewBox="0 0 816 838.86"`, wektorowy, domyślny w `Makefile` jako `MAP_IMAGE`.
- `pin-na-map.svg` — aktualny pin, domyślny `PIN_IMAGE`.
- `full-na-map.ai`, `pin-na-map.ai` — źródłowe AI z paczki.
- `north-america-map.ai` + pochodne PNG — starszy wariant artworku.
- `figma-section-895-2673.png`, `section-idea-1.png` — zrzuty/inspiracje sekcji.

---

## 4. Bieżący stan repo (2026-07-07)

- Gałąź `main`.
- Bieżący WIP upraszcza deliverable do jednej finalnej mapy.
- Aktywna ścieżka: `src/render_lsn_final_map.py` → `make map-final` → `data/output/lsn-map-final.html`.
- `Makefile` nie wystawia już targetów porównawczych `map-options`, `map-figma`, `map-geographic`, `map-d3`.
- Finalna mapa używa GIS/canvas basemapy stylowanej pod referencję klienta; nie używamy uproszczonego artwork overlay jako finalu.
- Bieżąca odpowiedź na feedback Michała: final ma domyślne `Full map` i opcjonalne `Short map`. `Short map` nie jest cropem viewportu; to osobny wygenerowany basemap, cięty geograficznie przed projekcją, z osobno filtrowanymi punktami.

### Generated outputs (`data/output/`, gitignored — nie commitować)
- `lsn-map-final.html` — jedyny aktywny client-facing output: D3/GIS final, jasna mapa, jeziora, Karaiby/Hawaje w tej samej mapie (bez insetu), zielone hot-zones, piny SVG, Points toggle, `Full map`/`Short map`, zoom/fullscreen.
- `lsn-north-america-final.svg` — pełny wygenerowany basemap.
- `lsn-north-america-final-short.svg` — wariant short, wygenerowany przez odrzucenie całych północnych detached components powyżej `SHORT_MAP_COMPONENT_MAX_LAT = 66.5`; bez prostokątnego cięcia poligonów.
- `lsn-north-america-final-hawaii.svg` — lokalny generated artifact dla hawajskiego display insetu.
- `clients_geocoded.csv`, `clients_enriched.xlsx`, `clients.geojson`, `geocode_exceptions.csv`, `run_summary.json`.
- `map.html` — starszy MapLibre dashboard; **artefakt, nie source of truth**.

### Lokalny proof/scratch (`.local-lab/`, gitignored)
- `.local-lab/proof/lsn-map-2026-06-30/0[1-5]-*.png` — screenshoty branded SVG + Figma component.
- `.local-lab/proof/lsn-map-2026-07-07/01-final-short-map-frame.png` — historyczny proof pierwszej wersji `Short map`.
- `.local-lab/proof/lsn-map-2026-07-07/02-final-short-map-layout-fixed.png` — historyczny proof viewport-cropu; nie traktować jako aktualnego rozwiązania.
- `.local-lab/proof/lsn-map-2026-07-07/03-final-short-map-data-safe-crop.png` — historyczny proof data-safe viewport-cropu; nie traktować jako aktualnego rozwiązania.
- `.local-lab/proof/lsn-map-2026-07-07/07-final-short-map-no-far-north-snap.png` — aktualny proof właściwej poprawki: osobny generated short basemap, naturalny component trim bez sztucznej linii cięcia, 1184 widoczne deploymenty w `Short map`; północne far-snap artefakty odfiltrowane.
- `.local-lab/proof/lsn-map/*.txt` — runtime proof (exact points, geographic).
- Te pliki **nie przenoszą się** na nową maszynę przez git; trzeba je wyregenerować (`make prototype` + agent-browser/screenshot).

---

## 5. Zweryfikowane ustalenia (ważne!)

- Demo pipeline w trybie `mock` → **1200/1200 matched, 100.0%, 0 wyjątków**.
- Pipeline z realnym `postal_reference.parquet` na **syntetycznym** sample → tylko **702/1200 (58.5%)**. To **nie** jest miara jakości finalnego Excela klienta — wynika z mieszania realnego parquetu z mockowymi/nieistniejącymi kodami w demo workbooku. Nie traktować tego jako gotowości produkcyjnej.
- Workbook `data/sample/north_america_generator_mapping_template.xlsx` ma mockowy arkusz `02_Postal_Reference_MOCK` dający 1200/1200.
- Template Excel ma syntetyczne kody pocztowe nieistniejące w realnym Census → do produkcji używać **prawdziwego** Excela klienta.
- Cel: **98%+ match** dla poprawnych kodów — ale nie twierdzić, że geokodowanie prod jest gotowe bez uruchomienia na realnym `data/input/clients.xlsx`.
- Bounds współrzędnych: US lat 18..72 lon -180..-60; CA lat 41..84 lon -142..-50; MX lat 14..33 lon -119..-86.
- `geo_key = country_code + "|" + postal_code_norm`. `postal_code_raw` traktować jako **tekst** (zachować leading zeros).
- Nowy SVG jest lepszym assetem wizualnym, ale **nie zawiera CRS/projekcji/georeferencji ani semantycznych ID regionów**. Branded prototype na nim = dobry do koncepcji/przeglądu, **nie** do geodezyjnej precyzji lon/lat.
- Figma node `895:2673` (plik `4NrYxpTRMC0mAtyuZMVXMK`) = pełny homepage mock z sekcją „Our Reach Across North America", **nie** gotowa spec interaktywnej mapy.
- Figma node `1715:3527` = `Map Zoom-In` component — odwzorowany w `render_lsn_figma_map.py`.

### Gates / jakość
- 2026-07-06 latest final-map fixes:
  - finalny renderer nie używa już Leafleta; HTML runtime to D3 zoom + jeden wspólny transform dla basemapy, pinów i hot-zon.
  - naprawiony projected extent: próbkuje całe krawędzie lon/lat, więc południowy Meksyk nie jest ucinany ani snapowany do jednej dolnej linii (`bottomLine: 0`).
  - admin1 granice są z Natural Earth 10m, bo 50m admin1 nie zawierał Meksyku; finalny SVG ma `subdivisionPaths: 97` zamiast 64.
  - hot-zones reclusterują się responsywnie na zoom/pinch/resize/mobile przez `visualViewport` + aktualny viewport/zoom.
  - ręczne białe owale jezior zostały usunięte; finalny SVG ma `ellipses: 0`.
  - Hawaje są display-only relokowane w tym samym SVG (`hawaii-display-inset`, `translate(255 1325) scale(0.62)`), zgodnie z referencją klienta, bez osobnej mapy HTML.
  - następny znany task wizualny: filtr mikro-elementów/wysp względem oryginalnego SVG klienta; najlepiej dodać area/extent filter w generatorze, nie edytować ręcznie SVG.
- 2026-07-07 boss-feedback update:
  - `Full map` zostaje domyślnym kadrem finalnej mapy.
  - Pierwsza implementacja była tylko fit/viewport cropem i została odrzucona. Następna próba z prostokątnym `lat_max=62.0` wycięła zbyt dużą część Kanady i 32 aktualne punkty demo. Aktualna implementacja generuje osobny `lsn-north-america-final-short.svg`, odrzuca całe detached components powyżej `SHORT_MAP_COMPONENT_MAX_LAT = 66.5`, nie przecina poligonów sztuczną linią, i przelicza dataset punktów dla frame'u.
  - Short-map punktów nie wolno snapować do usuniętej północnej geometrii. `filter_deployments_for_short_basemap()` usuwa punkty, które były na full basemapie, ale nie zostały na short basemapie, oraz far-snap artefakty dalej niż `SHORT_MAP_MAX_SNAP_DISTANCE_M = 100_000`.
  - Browser proof po kliknięciu `Short map`: `activeFrame.id=short`, `basemapSvg=data/output/lsn-north-america-final-short.svg`, `mapVariant=generated_clipped_basemap`, `rows=1200`, `visiblePoints=1184`, `excludedPoints=16`, `headerCount=1,184`, `imageAttrLength=799674`, `stage.height=577`.
  - Gate'y tej sesji: `python -m py_compile src/render_lsn_final_map.py` passed; `pytest tests/test_render_lsn_map_options.py -q` passed (`15 passed`); `pytest tests/ -q` passed (`51 passed`); `ruff check src/ tests/` passed; `make map-final` passed.
- `make test` → **51 passed**.
- `make lint` → all checks passed.
- `make typecheck` → **fails z 16 błędami pyright/pandas-geopandas typing** (zapisany **residual risk**, znany, nie blokuje).
- W sesji bez `.venv` (brak pandas globalnie) działa tylko `py_compile` + wywołania rendererów gdy CSV już istnieje.

---

## 6. Rekomendowany kierunek

1. `src/render_lsn_final_map.py` = source of truth finalnej mapy.
2. Generować tylko `data/output/lsn-map-final.html` przez `make map-final` albo `make prototype`.
3. Final ma zachować dopracowane zachowanie canvas: animowane piny, hot-zones z fade przy zoomie, Points jako osobna warstwa.
4. Pełny kadr mapy traktować jako główny. Skrócony kadr pokazywać wyłącznie jako wariację, bo dzisiejsze i przyszłe dane mogą obejmować północną Kanadę.
5. Jeśli klient chce dokładne punkty na ich oryginalnym artworku → poprosić o **georeferencję / CRS / control points**.

---

## 7. Guardrails (czego NIE robić)

- **Nie commitować** realnych danych klienta (`data/input/*.xlsx` gitignored).
- **Nie commitować** dużych generated outputów z `data/output/` (gitignored), chyba że wyraźnie wybrane jako deliverable.
- **Nie commitować** rootowego `NA_Map_Assets*.zip` (gitignored — dostarczony załącznik).
- **Nie edytować ręcznie** `data/output/*.html` — generować przez `make map-final`.
- **Nie traktować** `data/output/map.html` jako źródła prawdy.
- **Nie revertować** istniejących zmian bez wyraźnej zgody użytkownika.
- **Nie overengineerować** — najbliższy deliverable to porównywalny klikalny prototyp + plan.
- Dla `main`: robić PR, nie pchać bezpośrednio (reguła repo).

---

## 8. Źródła geokodowania

- **US**: Census TIGER/Line ZCTA520 2024 (~33 791 ZIP, public domain).
- **CA**: GeoNames CA_full (~899 779 kodów, CC-BY 4.0).
- **MX**: GeoNames MX (~32 448 kodów, CC-BY 4.0).
- **Mock fallback**: arkusz `02_Postal_Reference_MOCK` w template Excelu suplementuje niedopasowane kraje.

---

## 9. Przydatne ścieżki / kontekst zewn.

- Onboarding audit: `docs/ai/claude-code-onboarding-research.md`.
- Prompt templates: `docs/ai-prompts/`.
- Handoff doc history: `docs/lsn-map-state-and-plan-2026-06-19.md`.
- Screeny na Desktop Windows (`C:\Users\krnij\Desktop\lsn-map-*`) **nie są** częścią repo — w jednej z sesji zapis przez `/mnt/c` zwrócił `Permission denied`; proof trzymany w `.local-lab/`.
- `pyrightconfig.json` wskazuje na `.venv` → uruchamiać `pyright` z roota projektu.
