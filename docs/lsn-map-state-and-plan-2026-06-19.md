# LSN Map - stan i plan implementacji

Data: 2026-06-19

## Źródło zadania

Plik z briefem:

`/home/krn/.codex/attachments/397a5685-3b57-4e4c-bd85-bedd091775db/pasted-text-1.txt`

Klient potrzebuje praktycznego prototypu porównawczego na bazie dostarczonej mapy North America / LSN:

- nanieść deploymenty z Excela na dostarczoną mapę `.ai`,
- przygotować wariant z pinezkami,
- przygotować wariant z flagami,
- sprawdzić heatmapę na tej samej mapie,
- sprawdzić wariant heatmapa + pinezki,
- dodać zoom i desktopowy fullscreen,
- pokazać kilka opcji, bo finalny design sekcji nie jest jeszcze ustalony.

To jest praca rozpoznawczo-prezentacyjna. Pierwszy właściwy deliverable to czysty, powtarzalny prototyp i rekomendacja, nie pełna aplikacja ani finalny blok strony.

## Aktualny stan repo

Repo ma teraz dwa równoległe nurty:

1. Pipeline danych do geokodowania kodów pocztowych i eksportów.
2. Powtarzalny generator statycznego prototypu mapy klienta (`src/render_lsn_map_options.py`) i generowany HTML w `data/output/`.

Główny pipeline:

- `src/run_pipeline.py`
- `src/clean_clients.py`
- `src/normalize_postal.py`
- `src/postal_reference.py`
- `src/enrich.py`
- `src/qa.py`
- `src/export.py`
- `src/render_lsn_map_options.py`
- testy w `tests/`

Ważny aktualny dirty/untracked kontekst:

- `AGENTS.md`
- `data/assets/client-map/north-america-map.ai`
- `data/assets/client-map/`
- `data/reference/postal_reference.parquet`
- `src/build_reference.py`
- `src/render_lsn_map_options.py`
- `docs/ai-prompts/map_visualization_prompt.md`

Nie zakładać czystego worktree. Nie revertować tych zmian bez wyraźnej zgody użytkownika.

## Sprawdzone dowody

Assety lokalne:

- `data/assets/client-map/north-america-map.ai` jest lokalnie rozpoznawany jako jednostronicowy PDF/AI.
- `data/assets/client-map/north-america-map-ai-web.png` ma 1731x1800, RGB i nadaje się do użycia w przeglądarce.
- `data/assets/client-map/figma-section-895-2673.png` to zrzut sekcji Figma, nie finalna specyfikacja implementacyjna.
- Figma MCP dla pliku `4NrYxpTRMC0mAtyuZMVXMK`, node `895:2673`, zwraca pełny homepage mock. W środku jest sekcja z tekstami `Over 5,000 Systems Delivered` i `Our Reach Across North America` oraz statyczna mapa, ale nie ma specyfikacji interaktywnego trybu pinezki/flagi/heatmapa.

Wygenerowane HTML-e:

- `data/output/map.html`
  - prototyp MapLibre na prawdziwym basemapie,
  - osadza 702 deploymenty,
  - ma punkty, heatmapę i klastry,
  - nie używa dostarczonej mapy klienta.
- `data/output/lsn-map-options.html`
  - generowany przez `src/render_lsn_map_options.py`,
  - prototyp Leaflet na dostarczonej mapie klienta,
  - osadza 1200 demo deploymentów w trybie `mock`,
  - ma `L.CRS.Simple`, `L.imageOverlay`, tryb pinezek, tryb flag, heatmapę, hybrid, fit i fullscreen,
  - żyje w ignorowanym `data/output/`, ale jest powtarzalny przez `make prototype`.

Komendy walidacyjne uruchomione:

```bash
.venv/bin/python -m pytest tests/ -v
.venv/bin/ruff check src/ tests/
.venv/bin/python -m src.run_pipeline --input data/sample/north_america_generator_mapping_template.xlsx --output data/output
pyright src/ tests/
```

Wyniki:

- `pytest`: baseline 33 passed przed dodaniem testów trybów referencji; aktualny gate to 36 passed.
- `ruff`: all checks passed.
- pipeline na sample z domyślnym realnym parquetem: 702/1200 matched, 58.5%, warning below 98%.
- `pyright`: 16 errors, głównie typowanie pandas/GeoPandas oraz `src/build_reference.py`.

Niski match-rate na sample nie dowodzi, że produkcyjne geokodowanie jest złe. Wynika z tego, że demo workbook zawiera syntetyczne / nieistniejące kody pocztowe, a obecny kod preferuje `data/reference/postal_reference.parquet` przed mockowym arkuszem z workbooka.

### Run log - kontynuacja 2026-06-19

Świeży run po utworzeniu `GOAL.md`:

- `git status --short --branch`: dirty worktree na `main...origin/main`; zmodyfikowane `.gitignore`, `CLAUDE.md`, `Makefile`, `requirements.txt`, `src/postal_reference.py`, `src/run_pipeline.py`, `tests/test_pipeline.py`; untracked `AGENTS.md`, `GOAL.md`, `data/assets/`, `data/reference/`, `docs/ai-prompts/map_visualization_prompt.md`, `docs/lsn-map-state-and-plan-2026-06-19.md`, `src/build_reference.py`.
- `.venv/bin/python -m pytest tests/ -v`: baseline 33 passed przed dodaniem testów trybów referencji.
- `.venv/bin/ruff check src/ tests/`: all checks passed.
- `.venv/bin/python -m src.run_pipeline --input data/sample/north_america_generator_mapping_template.xlsx --output data/output`: 702/1200 matched, 58.5%, warning below 98%, 498 exceptions.
- `pyright src/ tests/`: 16 errors, głównie pandas/GeoPandas typing i `src/build_reference.py`.
- `git check-ignore`: `data/output/lsn-map-options.html` i `data/reference/postal_reference.parquet` są ignorowane; `data/assets/client-map/*.png` i `north-america-map.ai` nie są ignorowane i zostają source assetami.
- `.gitignore`: dodano `.local-lab/` jako lokalny katalog proof/scratch, żeby screenshoty QA nie mieszały się z committowanym source.
- `.venv/bin/python -m pytest tests/test_pipeline.py -v`: 11 passed po dodaniu trybów referencji.
- `.venv/bin/ruff check src/ tests/`: all checks passed po dodaniu trybów referencji.
- `.venv/bin/python -m src.run_pipeline --input data/sample/north_america_generator_mapping_template.xlsx --output data/output --reference-mode mock`: 1200/1200 matched, 100.0%, 0 exceptions.
- `.venv/bin/python -m src.run_pipeline --input data/sample/north_america_generator_mapping_template.xlsx --output /tmp/lsn2-map-parquet-check --reference-mode parquet`: 702/1200 matched, 58.5%, warning below 98%, 498 exceptions.
- `make prototype`: przechodzi; regeneruje pipeline demo w trybie `mock` i `data/output/lsn-map-options.html`.
- `make test`: 36 passed.
- `make lint`: all checks passed.
- `make typecheck`: failuje 16 błędami pyright, głównie pandas/GeoPandas typing i `src/build_reference.py`. To jest świadomy residual risk dla tego prototypu, nie runtime failure.
- `agent-browser` proof po poprawce osi Y Leaflet: `rows=1200`, `plotted=1200`, `clamped=0`.
- Lokalny serwer dla review: `http://127.0.0.1:8017/lsn-map-options.html`, HTTP 200.
- Po feedbacku wizualnym renderer został zmieniony z 1200 DOM markerów na pojedynczy canvas: tryby `Exact Points`, `Regions`, `Badges`, `Heatmap`, `Heat + Points`.
- Aktualny runtime proof: `.local-lab/proof/lsn-map/runtime-proof-exact-points.txt` pokazuje `active=Exact Points`, `rows=1200`, `plotted=1200`, `renderer=canvas-exact-points-and-region-aggregates`, `pointPlacement.lonLatLinear=1200`, `pointPlacement.clamped=0`, `markerIcons=0`, `markerCanvas=1`.
- Finalna walidacja po cleanupie renderera: `make prototype` passed, `make lint` passed, `make test` 36 passed, `make typecheck` nadal 16 pyright/pandas errors jako zapisany residual risk.
- Dodano wariant GIS-correct: `src/render_lsn_geographic_map.py`, target `make prototype-geographic`, output `data/output/lsn-map-geographic.html` i `data/output/lsn-north-america-geographic.svg`.
- GIS proof: `.local-lab/proof/lsn-map/runtime-proof-geographic.txt` pokazuje `active=Exact Points`, `rows=1200`, `plotted=1200`, `insideViewport=1200`, `rawInsideBasemap=1019`, `displayAdjusted=181`, `markerIcons=0`, `pointCanvas=1`, `zoomAnimation=false`.

### Run log - kontynuacja 2026-06-30

Nowy input od użytkownika:

- `NA_Map_Assets (1).zip`

Zawartość paczki:

- `NA_Map_Assets/Full_NA_MAP.ai`
- `NA_Map_Assets/NEW NA MAP.svg`
- `NA_Map_Assets/Pin_NA_Map.ai`
- `NA_Map_Assets/Pin_NA_Map.svg`

Wnioski z rozpoznania:

- `NEW NA MAP.svg` ma `viewBox="0 0 816 838.86"`, 740 ścieżek, 144 polygony i tylko podstawowe style fill.
- SVG jest sensownym wektorowym assetem do branded preview, ale nie zawiera CRS, projekcji, georeferencji ani semantycznych ID regionów.
- `Pin_NA_Map.svg` nadaje się jako marker w canvas rendererze.
- Samo przejście z PNG/AI na SVG poprawia jakość wizualną, ale nie rozwiązuje dokładności lon/lat. Do exact placement produkcyjnie nadal potrzebna jest mapa GIS albo georeferencja/control points.

Zmiany implementacyjne:

- Dodano source assety:
  - `data/assets/client-map/new-na-map.svg`
  - `data/assets/client-map/pin-na-map.svg`
  - `data/assets/client-map/full-na-map.ai`
  - `data/assets/client-map/pin-na-map.ai`
- `src/render_lsn_map_options.py` czyta teraz wymiary SVG lub PNG i osadza mapę/pin jako data URI.
- Domyślne assety renderera to `new-na-map.svg` i `pin-na-map.svg`.
- `Makefile` dostał `PIN_IMAGE` i przekazuje `--pin-image` do `map-options`.
- UI branded prototype ma teraz tryby `Pins`, `Regions`, `Flags`, `Heatmap`, `Heat + Pins`.
- `Pins` i `Heat + Pins` rysują pin SVG na canvasie, nie tworzą 1200 DOM markerów.
- `Flags` zostały zmienione z prostych badge'y na canvasowe exact flag markers.
- Dodano `src/render_lsn_figma_map.py`, osobny renderer Figma node `1715:3527` (`Map Zoom-In`), z dwoma wariantami `Default`/`Variant2` w jednym HTML.
- `lsn-map-figma.html` zachowuje crop ratios z Figmy, ale mapę, punkty i klastry rysuje dynamicznie z CSV, zamiast używać prekomponowanego obrazka z markerami.

Walidacja w tej sesji:

- `python3 -m py_compile src/render_lsn_map_options.py`: passed.
- `python3 -m py_compile src/render_lsn_figma_map.py`: passed.
- `python3 -m src.render_lsn_map_options --input data/output/clients_geocoded.csv --map-image data/assets/client-map/new-na-map.svg --pin-image data/assets/client-map/pin-na-map.svg --output data/output/lsn-map-options.html`: passed.
- `make map-options`: passed.
- `make map-figma`: passed.
- Local preview: `http://127.0.0.1:8017/lsn-map-options.html` HTTP 200.
- Figma preview: `http://127.0.0.1:8017/lsn-map-figma.html` HTTP 200.
- Browser runtime proof: `rows=1200`, `plotted=1200`, `sourceMap=data/assets/client-map/new-na-map.svg`, `sourcePin=data/assets/client-map/pin-na-map.svg`, `renderer=svg-map-canvas-pins-and-region-aggregates`, `markerIcons=0`, `markerCanvas=1`, `pinSvg=true`, `zoomAnimation=false`.
- Browser runtime proof Figma: `figmaNode=1715:3527`, `variants=["overview","zoom"]`, `rows=1200`, `plotted=1200`, `clusters=38`, `renderer=figma-map-zoom-in-canvas`.
- Proof screenshoty:
  - `.local-lab/proof/lsn-map-2026-06-30/01-new-svg-pins.png`
  - `.local-lab/proof/lsn-map-2026-06-30/02-new-svg-flags.png`
  - `.local-lab/proof/lsn-map-2026-06-30/03-new-svg-heatmap.png`
  - `.local-lab/proof/lsn-map-2026-06-30/04-new-svg-heat-pins.png`
  - `.local-lab/proof/lsn-map-2026-06-30/05-figma-map-component.png`
- `02-new-svg-flags.png`, `03-new-svg-heatmap.png`, `04-new-svg-heat-pins.png`, `05-figma-map-component.png` obejrzane przez `view_image`.

Ograniczenia walidacji:

- W tej sesji `.venv` nie istnieje, a globalny `python3` nie ma `pandas`, więc pełne `make prototype`, `make test`, `make lint` nie było odpalane po zmianie assetów.
- Sprawdzony został standalone renderer, który nie wymaga pandas, bo korzysta z istniejącego `data/output/clients_geocoded.csv`.
- Próba zapisu screenshotów na `C:\Users\krnij\Desktop` przez `/mnt/c` zwróciła `Permission denied`; proof zapisano pod `.local-lab`.

Repo classification przed cleanupem:

| Kategoria | Pliki / katalogi | Decyzja |
| --- | --- | --- |
| Source docs | `GOAL.md`, `AGENTS.md`, `docs/lsn-map-state-and-plan-2026-06-19.md` | Trzymać jako source of truth; aktualizować na bieżąco. |
| Pipeline source | `src/*.py`, `tests/*.py`, `Makefile`, `requirements.txt`, `.gitignore`, `README.md`, `CLAUDE.md` | Commit candidates po cleanupie i walidacji. |
| Client/demo assets | `data/assets/client-map/north-america-map.ai`, `data/assets/client-map/*.png` | Trzymać pod `data/assets/client-map/`; rootowy `.ai` został przeniesiony do katalogu assetów. |
| Generated outputs | `data/output/*` | Nie traktować jako source of truth; regenerować komendą. |
| Large local reference | `data/reference/postal_reference.parquet` | Lokalny build artifact, gitignored; zostawić poza commitem. |
| Reference placeholder | `data/reference/.gitkeep` | Commit candidate tylko jako pusty placeholder katalogu; realny parquet zostaje ignorowany. |
| Cache/bytecode | `__pycache__`, `.pytest_cache`, `.ruff_cache` | Nie commitować. |
| Windows metadata | `data/sample/*.xlsx:Zone.Identifier` | Nie commitować; `.gitignore` już łapie `*:Zone.Identifier`. |

## Technologie na 2026-06-19

Lokalnie sprawdzone wersje npm:

- `leaflet`: 1.9.4
- `maplibre-gl`: 5.24.0
- `leaflet.heat`: 0.2.0

Sprawdzone dokumentacje / źródła:

- Leaflet dokumentuje `CRS.Simple` dla map niegeograficznych oraz `L.ImageOverlay`, `L.Marker` i `fitBounds`.
- Leaflet ostrzega, żeby nie zakładać automatycznie, że jednostki mapy są tym samym co piksele obrazu. To jest istotne przy mapowaniu realnego lat/lon na ilustrację.
- Leaflet.heat obsługuje `L.heatLayer([...], { radius })`, z intensywnością jako opcjonalną trzecią wartością punktu.
- MapLibre GL JS jest rendererem WebGL/vector-tile i ma natywne wzorce dla GeoJSON, heatmap, klastrów, popupów i fullscreen.

Wniosek praktyczny:

- Dla dostarczonej mapy `.ai` najlepszy jest Leaflet + image overlay, ale jako branded regional overview.
- Dla prawdziwej mapy geograficznej z precyzyjnym pan/zoom/cluster najlepszy jest MapLibre.
- Nie wymuszać na ilustracyjnej mapie klienta precyzji GIS. Jeśli exact placement na artworku jest wymagany, potrzebne są punkty kontrolne GCP i georeferencja/rubber-sheeting.

## Matryca decyzji

| Opcja | Zastosowanie | Plusy | Minusy | Rekomendacja |
| --- | --- | --- | --- | --- |
| Leaflet + `CRS.Simple` + image overlay | Mapa klienta z Pins/Regions/Flags/Heat/Heat + Pins | Najlepiej pasuje do briefu, proste, bez build stepu, zoom/fullscreen łatwe | Punkty/piny na artworku są diagnostyczne, nie GIS | Pierwszy rekomendowany deliverable |
| MapLibre GL JS + GeoJSON | Prawdziwy dashboard geograficzny | Dokładna geografia, natywne heatmapy/klastry, dobra wydajność | Nie używa wyglądu mapy klienta | Zachować jako wariant porównawczy |
| Statyczny SVG/obraz | Screenshot do decka/sprzedaży | Szybkie i kontrolowane | Brak zoomu/fullscreen/interakcji | Tylko jako eksport screenshotów |
| React/WordPress block teraz | Finalna integracja strony | Reużywalne produkcyjnie | Za wcześnie przed decyzją designową | Odłożyć |
| GCP/georeferencja artworku | Exact-ish punkty na dostarczonym obrazie | Da się skalibrować obraz bez porzucania brandingu | Wymaga landmarków, walidacji i utrzymania transformu | Następny krok tylko jeśli klient wymaga dokładnych punktów na artworku |

## Zrealizowany kształt implementacji

Zbudowany jest jeden powtarzalny generator statycznego HTML:

- `src/render_lsn_map_options.py`,
- wejście: `clients_geocoded.csv` albo bezpośredni output pipeline,
- asset: domyślnie `data/assets/client-map/new-na-map.svg`,
- pin: domyślnie `data/assets/client-map/pin-na-map.svg`,
- output: `data/output/lsn-map-options.html`,
- Figma output: `data/output/lsn-map-figma.html`,
- bez npm i bundlera,
- zależności z CDN przypięte wersją,
- tryby w jednym UI: Pins, Regions, Flags, Heatmap, Heat + Pins,
- regionalne agregaty są rysowane jednym canvas layerem; nie ma 1200 markerów DOM,
- piny są rysowane na canvasie z SVG klienta; nie ma 1200 markerów DOM,
- heatmapa jest liczona z agregatów regionalnych, nie z pseudo-losowych punktów,
- przyciski fullscreen i fit,
- panel status/country summary,
- runtime proof i screenshoty są w `.local-lab/proof/lsn-map/`.

To daje szybkie porównanie opcji i nie miesza go jeszcze z finalną implementacją strony.

## Strategia danych

Potrzebne są dwa jawne tryby danych:

1. Tryb demo / porównawczy:
   - używa mockowej referencji z workbooka albo wygenerowanego demo exportu,
   - cel: ocena wizualna,
   - może pokazać pełne 1200 sample pointów, jeśli jest jasno opisane jako demo.

2. Tryb production / client-data:
   - używa realnego Excela z `data/input/`,
   - używa realnej referencji parquet/fallback,
   - raportuje match-rate uczciwie,
   - nie wolno claimować 98% bez runu na prawdziwym workbooku klienta.

Kod ma teraz jawny przełącznik `--reference-mode auto|mock|parquet|synthetic`. `mock` jest trybem demo/proof, `parquet` jest trybem real/client-data.

## Strategia projekcji na mapie klienta

Dostarczona mapa jest ilustracją. Aktualny prototyp używa deterministycznych anchorów regionalnych:

- grupować rekordy po `service_region` i kraju,
- rysować czytelne bubbles/heat na anchorach regionów,
- rysować piny/flagi jako exact marker variants, ale traktować to jako visual comparison na artworku, nie GIS proof,
- trzymać anchory w source jako named constants,
- w proof/handoff zaznaczać, że to overlay prezentacyjny, nie geodezyjna basemapa.

Nie robić ręcznego point-by-point placementu. Nie skaluje się do prawdziwego Excela i wygląda fałszywie na niereferencjonowanym artworku.

## Plan realizacji

## Backlog wykonawczy

Przed dalszą implementacją ten backlog jest source of truth. Statusy aktualizować przy każdej istotnej zmianie.

| ID | Obszar | Zadanie | Status | Kryterium akceptacji | Dowód |
| --- | --- | --- | --- | --- | --- |
| R-01 | Rozpoznanie | Przeczytać `GOAL.md`, `AGENTS.md`, plan doc i brief z attachmentu | done | Wszystkie źródła przeczytane w aktualnej sesji | Odczyty `sed` w logu sesji |
| R-02 | Rozpoznanie | Sklasyfikować tracked/untracked/generated/assets/cache | done | Każda grupa ma decyzję przed cleanupem | Tabela `Repo classification przed cleanupem` |
| R-03 | Rozpoznanie | Uruchomić minimalny zestaw walidacji | done | Wyniki pytest/ruff/pipeline/pyright zapisane | Sekcja `Run log - kontynuacja 2026-06-19` |
| C-01 | Cleanup | Uporządkować assety mapy klienta | done | Brak luźnego rootowego assetu bez decyzji; web-ready asset ma stabilną ścieżkę | `git status`, `rg --files data/assets` |
| C-02 | Cleanup | Uporządkować `.gitignore` pod dane, reference i outputy | done | Realne dane i duże referencje są chronione; source assety nie są przypadkiem ignorowane | `.gitignore`, `git check-ignore`, `git status --ignored` |
| C-03 | Cleanup | Uzgodnić README/Makefile/CLAUDE z realnym flow | done | README pokazuje działające komendy demo/prod/render | `README.md`, `CLAUDE.md`, `make prototype` |
| C-04 | Cleanup | Usunąć albo oznaczyć przestarzałe twierdzenia dokumentacyjne | done | Brak sprzeczności typu "mock only" vs "parquet default" | `README.md`, `CLAUDE.md`, `AGENTS.md` |
| D-01 | Data/pipeline | Dodać jawny tryb referencji `auto/mock/parquet/synthetic` | done | Sample mock daje 1200/1200; parquet zachowuje realny 702/1200 | dwa runy CLI w run logu |
| D-02 | Data/pipeline | Dodać testy dla nowego trybu referencji | done | Test pokrywa mock mode i auto/parquet behavior bez zależności od lokalnego parquetu | `tests/test_pipeline.py`, 11 passed |
| D-03 | Data/pipeline | Rozstrzygnąć `pyright` jako gate albo residual risk | done | Pyright przechodzi albo dokumentuje się świadomy residual risk | `make typecheck` fail 16 errors; residual risk zapisany |
| M-01 | Renderer | Dodać powtarzalny renderer mapy klienta | done | `data/output/lsn-map-options.html` powstaje z komendy, nie ręcznie | `src/render_lsn_map_options.py`, `make prototype` |
| M-02 | Renderer | Zaimplementować tryby Regions/Flags/Heat/Hybrid | done | UI pozwala przełączać wszystkie tryby | browser proof screenshots |
| M-03 | Renderer | Utrwalić transform lon/lat -> image space jako named constants | done | Transform jest w source, nie w ręcznie edytowanym HTML | `src/render_lsn_map_options.py` `projection` constants |
| M-04 | Renderer | Dodać fit/fullscreen i panel summary | done | Fit/fullscreen działają na desktopie; panel pokazuje liczbę rekordów/statusy | browser proof i UI controls |
| M-05 | Renderer | Dodać Figma `Map Zoom-In` component renderer | done | `lsn-map-figma.html` pokazuje overview i zoom crop zgodnie z node `1715:3527` | `make map-figma`, `05-figma-map-component.png` |
| Q-01 | Visual QA | Wygenerować proof 1920x1080 i 1440x900 | done | Screenshoty pokazują nieblank mapę i controls | `.local-lab/proof/lsn-map/*.png` |
| Q-02 | Visual QA | Sprawdzić tryby Regions, Flags, Heatmap, Hybrid | done | Każdy tryb ma screenshot albo jednoznaczny proof | proof ledger poniżej |
| DOC-01 | Dokumentacja | Utrzymać `GOAL.md`, `AGENTS.md`, plan doc jako spójny system | done | Dokumenty nie mają sprzecznego next action/statusu | `AGENTS.md`, ten dokument |
| DOC-02 | Dokumentacja | README zaktualizowany dopiero po realnym flow | done | README commands działają lokalnie | `README.md`, `make prototype` |
| REC-01 | Klient | Przygotować finalną rekomendację wariantów | done | Krótki tekst: Regions, Flags, Heatmap, Hybrid, MapLibre/GCP vs artwork | sekcja `Finalna rekomendacja` |

Explicit out-of-scope do czasu decyzji klienta:

- WordPress block / React app.
- Produkcyjny endpoint danych.
- Claim o 98% geokodowania bez realnego workbooka klienta.
- Ręczne point-by-point placementy markerów.
- Exact GIS na niereferencjonowanym artworku bez osobnego etapu GCP/georeferencji.

### Slice 1 - Uczynić obecny prototyp powtarzalnym

Deliverables:

- `src/render_lsn_map_options.py`
- `make map-options` albo równoważna komenda
- generowany `data/output/lsn-map-options.html`

Acceptance:

- wygenerowany HTML otwiera się bezpośrednio w przeglądarce,
- zawiera Pins, Regions, Flags, Heatmap i Heat + Pins,
- używa dostarczonej mapy klienta,
- osadza dokładnie wiersze z wybranego źródła danych,
- nie wymaga ręcznej edycji wygenerowanego HTML.

### Slice 2 - Naprawić rozdział demo vs production data

Deliverables:

- flaga CLI typu `--reference-mode auto|mock|parquet|synthetic` albo `--prefer-mock-reference`,
- notka w README o zachowaniu sample/demo,
- test potwierdzający mock mode z 1200/1200 sample match.

Acceptance:

- demo mode produkuje pełną wizualizację sample,
- production mode zachowuje realną referencję,
- warning poniżej 98% zostaje dla real-data runów.

### Slice 3 - Visual QA i proof pack

Deliverables:

- screenshoty 1920x1080 i 1440x900,
- po jednym screenshocie per tryb albo minimum Regions + Flags + Heat + Hybrid,
- krótki opis dla klienta, co pokazuje każdy tryb.

Acceptance:

- mapa nie jest blank,
- controls są widoczne i czytelne,
- markery/heat nie psują czytelności mapy,
- fullscreen i fit działają na desktopie.

### Slice 4 - Rekomendacja dla klienta

Treść rekomendacji:

- Regions są najlepszym domyślnym wariantem na dostarczonym artworku: czytelne i uczciwe wobec braku georeferencji.
- Flags są przydatne, jeśli kraj/liczba mają być bardzo czytelne, ale są mniej mapowe niż bubbles.
- Heatmapa jest najlepsza do strategicznej gęstości, nie do exact lookupu klienta.
- Heat + Pins dobrze działa jako stakeholder demo, ale może sugerować precyzję, której artwork nie ma.
- Jeśli chcą precyzyjną mapę operacyjną, użyć MapLibre real geography. Jeśli chcą exact punkty na tym artworku, wykonać GCP/georeferencję. Jeśli chcą branded sekcję, użyć Leaflet artwork prototype.

### Slice 5 - Integracja później

Dopiero po wyborze kierunku:

- spakować jako sekcję/blok WordPress albo embed statycznego assetu,
- zdecydować, czy dane są statyczne, regenerowane przy deployu, czy ładowane z endpointu,
- skompresować obraz i osadzone dane,
- zrobić privacy review, jeśli realne nazwy klientów zostaną w tooltipach.

## Proof ledger

Artefakty proof są lokalne i gitignored, bo to wynik QA, nie source code:

| Dowód | Co potwierdza |
| --- | --- |
| `.local-lab/proof/lsn-map/runtime-proof-exact-points.txt` | Runtime `active=Exact Points`, `rows=1200`, `plotted=1200`, `renderer=canvas-exact-points-and-region-aggregates`, `pointPlacement.lonLatLinear=1200`, `pointPlacement.clamped=0`, `markerIcons=0`. |
| `.local-lab/proof/lsn-map/01-artwork-exact-points.png` | Artwork renderer pokazuje pojedyncze punkty, bez badge'y i clusterów. |
| `.local-lab/proof/lsn-map/02-gis-exact-points.png` | GIS renderer pokazuje pojedyncze punkty na Albers Equal Area, bez badge'y i clusterów. |
| `.local-lab/proof/lsn-map/regions-bubbles-1920x1080.png` | Regions renderują się jako czytelne bubbles na artworku, UI i panel summary są widoczne. |
| `.local-lab/proof/lsn-map/region-badges-1920x1080.png` | Badges działają jako osobny wariant agregowany po regionie/kraju. |
| `.local-lab/proof/lsn-map/heat-regions-1920x1080.png` | Heatmapa działa na agregatach regionalnych na tym samym artworku. |
| `.local-lab/proof/lsn-map/hybrid-regions-1920x1080.png` | Historyczny proof dawnego hybrydowego wariantu przed dodaniem obecnego Heat + Points. |
| `.local-lab/proof/lsn-map/regions-bubbles-1440x900.png` | Desktop 1440x900 zachowuje czytelne controls, panel i mapę po resize/fitu. |
| `.local-lab/proof/lsn-map-2026-06-30/01-new-svg-pins.png` | Nowy SVG mapy klienta z pinami z `Pin_NA_Map.svg`, canvas renderer, bez DOM markerów. |
| `.local-lab/proof/lsn-map-2026-06-30/02-new-svg-flags.png` | Nowy SVG mapy klienta z exact flag markers rysowanymi na canvasie. |
| `.local-lab/proof/lsn-map-2026-06-30/03-new-svg-heatmap.png` | Nowy SVG mapy klienta z heatmapą agregatów regionalnych. |
| `.local-lab/proof/lsn-map-2026-06-30/04-new-svg-heat-pins.png` | Nowy SVG mapy klienta z heatmapą i pinami w jednym widoku. |
| `.local-lab/proof/lsn-map-2026-06-30/05-figma-map-component.png` | Implementacja Figma node `1715:3527`: overview + zoom crop, dynamiczne punkty i klastry z CSV. |

Proof był oglądany ręcznie przez `view_image` dla Exact Points na artworku i GIS oraz wcześniej dla Regions, Badges, Heat, Hybrid i 1440x900.

## Finalna rekomendacja

- Regions są najlepszym domyślnym wariantem do rozmowy z klientem na dostarczonym artworku: są czytelne i nie udają dokładności pojedynczych adresów.
- Flags są dobre do szybkiego porównania krajów/liczb, ale są bardziej dashboardowe niż mapowe.
- Heatmapa najlepiej pokazuje strategiczną gęstość, ale nie nadaje się do dokładnego lookupu konkretnego deploymentu.
- Heat + Pins jest mocne jako stakeholder demo, ale w finalnej sekcji trzeba jasno traktować je jako overview, nie proof geodezyjny.
- Nowy SVG z paczki klienta jest najlepszym branded assetem do dalszej prezentacji, ale nie zmienia rekomendacji technicznej: exact lon/lat wymaga GIS albo georeferencji.
- Jeśli klient chce branded sekcję na swojej mapie, zostać przy Leaflet + artwork.
- Jeśli klient chce precyzyjną mapę operacyjną, wrócić do MapLibre real geography.
- Jeśli klient koniecznie chce precyzyjne punkty na tej ilustracji, zrobić georeferencję przez GCP/control points i walidację holdout landmarków.

## Znane ryzyka

- `data/output/lsn-map-options.html` jest ignorowanym artefaktem, ale jest powtarzalny przez `make prototype`; źródłem prawdy jest `src/render_lsn_map_options.py`.
- Artwork nie jest geodezyjną basemapą GIS. Tryb Pins na artworku jest diagnostycznym rzutem/overview na ilustrację, a regionalne tryby celowo używają anchorów.
- Heatmapa na ilustracji może sugerować precyzję, której artwork nie ma.
- `make typecheck` / `pyright` nadal failuje 16 błędami typowania pandas/GeoPandas. Runtime gate'y `make test`, `make lint` i `make prototype` przechodzą.
- W sprawdzonym stanie repo nie ma realnego Excela klienta.
- Link Figma został zweryfikowany przez MCP, ale finalny design według briefu nadal nie istnieje. Nie overfitować do aktualnego homepage mocka.

## Następna najlepsza akcja

Pokazać klientowi prototyp pod lokalnym URL albo wysłać screenshoty proof i zebrać decyzję, który wariant ma iść do finalnej sekcji. Dopiero po tej decyzji planować WordPress/React/embed.
