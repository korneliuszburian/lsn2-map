# Handoff — LSN2 Map (North America Generator Deployment Mapping)

> **Pierwsza rzecz po odpaleniu repo: przeczytaj ten plik (`handoff.md`) od deski do deski.**
> To jest single source of truth dla bieżącego stanu pracy, decyzji, known-issues i tego, jak uruchomić projekt na nowej maszynie.
> Datum ostatniej aktualizacji: **2026-07-06**.

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

# 4) prototyp mapy klienta (branded, na new-na-map.svg)
make prototype

# 5) podgląd w przeglądarce
make serve   # http://127.0.0.1:8017/lsn-map-options.html
```

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
- oraz **statyczne prototypy HTML mapy klienta** do porównania wariantów wizualnych (pinezki / flagi / heatmapa / hybryda / zoom / fullscreen).

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
| `make map-options` | Render `lsn-map-options.html` (branded, na `new-na-map.svg`) |
| `make map-figma` | Render `lsn-map-figma.html` (Figma node `1715:3527`, `Map Zoom-In`) |
| `make map-geographic` | Render `lsn-map-geographic.html` (GIS-correct, Albers Equal Area) |
| `make prototype` | `run-demo` + `map-options` |
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
- `src/render_lsn_map_options.py` — **source of truth** dla `lsn-map-options.html` (branded, na artworku klienta)
- `src/render_lsn_figma_map.py` — render `lsn-map-figma.html` (Figma `Map Zoom-In`)
- `src/render_lsn_geographic_map.py` — render `lsn-map-geographic.html` (GIS-correct, realne granice w stylu LSN)

Tryby referencji: `auto`, `mock`, `parquet`, `synthetic`. Priorytet `auto`: `--reference` > domyślny parquet > Excel mock > synthetic.

### Asset artworku (`data/assets/client-map/`)
- `new-na-map.svg` — aktualny branded asset (z paczki `NA_Map_Assets`), `viewBox="0 0 816 838.86"`, wektorowy, domyślny w `Makefile` jako `MAP_IMAGE`.
- `pin-na-map.svg` — aktualny pin, domyślny `PIN_IMAGE`.
- `full-na-map.ai`, `pin-na-map.ai` — źródłowe AI z paczki.
- `north-america-map.ai` + pochodne PNG — starszy wariant artworku.
- `figma-section-895-2673.png`, `section-idea-1.png` — zrzuty/inspiracje sekcji.

---

## 4. Bieżący stan repo (2026-07-06)

- Gałąź `main`.
- Ostatni commit lokalny/na `origin/main` po tej rundzie dotyczy poprawy GIS renderer + dodania trybu `Flags`.
- Wszystkie źródła i assety są commitowane i wypchnięte.
- Aktualny stan roboczy po komicie: czysty (poza ignorowanymi artefaktami: `.venv/`, `data/output/`, `data/reference/*.parquet`, `.local-lab/`).
- W tej sesji zaktualizowano `src/render_lsn_geographic_map.py`:
  - doraźny styl GIS mapy bazującej na Natural Earth:
    - kolory obszarów US/CA/MX pod brand,
    - obrys państw i granice stanów/prowincji,
    - opcjonalna siatka geograficzna,
    - ciemniejszy, stonowany background.
  - rozszerzony HTML `lsn-map-geographic.html`:
    - tryb `Flags` (canvasowe flagi) obok `Points`, `Clusters`, `Heatmap`, `Heat + Points`,
    - `Fit` + `Fullscreen`,
    - lepszy, stabilny overlay geograficzny na `CRS.Simple` + image overlay.
  - dodatkowe opcje CLI: `--grid-spacing`, `--no-grid`.
- Komendy uruchomieniowe sprawdzone po zmianach:
  - `make map-geographic` ✅
  - `make prototype-geographic` ✅
  - `python3 -m py_compile src/render_lsn_geographic_map.py` ✅
  - `ruff check src/render_lsn_geographic_map.py` ✅

### Generated outputs (`data/output/`, gitignored — nie commitować)
- `lsn-map-options.html` — branded prototype, tryby `Pins`/`Regions`/`Flags`/`Heatmap`/`Heat + Pins` + fit + fullscreen. **Artefakt — nie edytować ręcznie**, regenerować przez `make map-options`.
- `lsn-map-figma.html` — Figma `Map Zoom-In`, dwa warianty `Default`/`Variant2` stacked.
- `lsn-map-geographic.html` — GIS-correct, Albers Equal Area, tryby exact points/flags/clusters/heat/heat+points.
- `clients_geocoded.csv`, `clients_enriched.xlsx`, `clients.geojson`, `geocode_exceptions.csv`, `run_summary.json`.
- `map.html` — starszy MapLibre dashboard; **artefakt, nie source of truth**.

### Lokalny proof/scratch (`.local-lab/`, gitignored)
- `.local-lab/proof/lsn-map-2026-06-30/0[1-5]-*.png` — screenshoty branded SVG + Figma component.
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
- `make test` → **36 passed**.
- `make lint` → all checks passed.
- `make typecheck` → **fails z 16 błędami pyright/pandas-geopandas typing** (zapisany **residual risk**, znany, nie blokuje).
- W sesji bez `.venv` (brak pandas globalnie) działa tylko `py_compile` + wywołania rendererów gdy CSV już istnieje.

---

## 6. Rekomendowany kierunek

1. `src/render_lsn_map_options.py` = source of truth prototypu branded.
2. Pierwsza wersja: **statyczny HTML bez npm/build step** — klient potrzebuje porównania koncepcji.
3. Dla mapy klienta: Leaflet z `CRS.Simple` / image overlay (bo `.ai`/`.svg` to nie projekcja GIS).
4. Pozycje na artworku traktować jako **regionalne agregaty**, dobre do koncepcji, nie do precyzji.
5. Równolegle trzymać wariant „real geography" (`lsn-map-geographic.html`) jako kierunek dla exact deployment points.
6. **Nie budować** od razu WordPress bloku / React appki. Najpierw client-review HTML + screenshoty/proof.
7. Jeśli klient chce dokładne punkty na brandowanej mapie → poprosić o **georeferencję / CRS / control points** albo przygotować własną mapę GIS w ich stylu.

---

## 7. Guardrails (czego NIE robić)

- **Nie commitować** realnych danych klienta (`data/input/*.xlsx` gitignored).
- **Nie commitować** dużych generated outputów z `data/output/` (gitignored), chyba że wyraźnie wybrane jako deliverable.
- **Nie commitować** rootowego `NA_Map_Assets*.zip` (gitignored — dostarczony załącznik).
- **Nie edytować ręcznie** `data/output/*.html` — generować przez `make map-*`.
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
