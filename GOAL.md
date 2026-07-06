# /goal - domknąć LSN map end-to-end, najpierw plan i cleanup, potem implementacja

## Status wykonania - 2026-07-06

Nowy etap: przygotowany został wariant finalny GIS-correct, który ma spełniać docelowe wymagania wizualne (jasne tło, białe granice, małe zielone punkty, zielone hot-zones bez czerwono-żółtej heatmapy) i nie blokuje istniejących porównawczych rendererów.

- dodany nowy source renderer: `src/render_lsn_final_map.py`
- dodany nowy target: `make map-final` → `data/output/lsn-map-final.html` + `data/output/lsn-north-america-final.svg`
- target `map-final` używa tego samego GIS flow co `map-geographic` (Natural Earth + Albers Equal Area), ale inny styl + nowe UI (tryby: Hot-zones, Points, Pins, Flags + Fit + Fullscreen)
- zachowany `make map-geographic` jako oddzielny wariant porównawczy
- styl finalny domyślnie pokazuje `Hot-zones + Points`
- finalnie wyraźnie utrzymana zasada: dostarczony `.ai/.svg` to asset wizualny, nie źródło prawdy geograficznej

## Status wykonania - 2026-06-30

Początkowy milestone 2026-06-30 dotyczył finalizacji porównawczych prototypów na nowym `NA_Map_Assets (1).zip`.

## Status wykonania - 2026-06-30 (archiwum)

Goal pozostawał wykonany jako prototyp porównawczy, a bieżący WIP aktualizował branded mapę po otrzymaniu `NA_Map_Assets (1).zip`.

Potwierdzone w tamtej sesji:

- nowy asset `NEW NA MAP.svg` został przeniesiony do `data/assets/client-map/new-na-map.svg`;
- nowy asset `Pin_NA_Map.svg` został przeniesiony do `data/assets/client-map/pin-na-map.svg`;
- renderer obsługuje teraz SVG/PNG mapy i osobny asset pina;
- aktualny UI branded prototype ma tryby `Pins`, `Regions`, `Flags`, `Heatmap`, `Heat + Pins`;
- `Pins` i `Heat + Pins` używają canvasowego rysowania pina SVG, nie DOM markerów;
- `Flags` są teraz canvasowymi exact flag markers, a nie prostymi badge'ami;
- dodano osobny renderer `src/render_lsn_figma_map.py` dla Figma node `1715:3527` (`Map Zoom-In`);
- `make map-figma` generuje `data/output/lsn-map-figma.html` z dwoma wariantami `Default`/`Variant2`;
- standalone renderer przeszedł `python3 -m py_compile src/render_lsn_map_options.py`;
- standalone renderer wygenerował `data/output/lsn-map-options.html` z `new-na-map.svg` i `pin-na-map.svg`;
- browser proof pokazuje `rows=1200`, `plotted=1200`, `markerIcons=0`, `markerCanvas=1`;
- Figma browser proof pokazuje `figmaNode=1715:3527`, `variants=["overview","zoom"]`, `rows=1200`, `plotted=1200`, `clusters=38`;
- proof screenshoty są w `.local-lab/proof/lsn-map-2026-06-30/`.

Ograniczenie: w tej sesji `.venv` nie istnieje, więc pełne `make prototype/test/lint` trzeba odpalić dopiero po odtworzeniu środowiska. Techniczna rekomendacja się nie zmienia: nowy SVG jest lepszym artworkiem, ale bez CRS/georeferencji nie daje produkcyjnie dokładnych lon/lat.

## Status wykonania - 2026-06-19

Goal wykonany jako prototyp porównawczy i handoff repo.

Potwierdzone:

- `make prototype` regeneruje demo pipeline i `data/output/lsn-map-options.html`;
- demo/mock pipeline daje `1200/1200` matched i `0` exceptions;
- real/parquet sample zachowuje uczciwy wynik `702/1200`, `58.5%`, z warningiem poniżej 98%;
- renderer miał wtedy tryby `Exact Points`, `Regions`, `Badges`, `Heatmap`, `Heat + Points`, fit i fullscreen; bieżący UI z 2026-06-30 to `Pins`, `Regions`, `Flags`, `Heatmap`, `Heat + Pins`;
- renderer po feedbacku używa canvas exact-points i regionalnych agregatów, nie 1200 markerów DOM;
- browser proof: `.local-lab/proof/lsn-map/runtime-proof-exact-points.txt` pokazuje `active=Exact Points`, `rows=1200`, `plotted=1200`, `pointPlacement.lonLatLinear=1200`, `pointPlacement.clamped=0`, `markerIcons=0`;
- screenshoty proof są w `.local-lab/proof/lsn-map/`;
- `make test`: 36 passed;
- `make lint`: all checks passed;
- `make typecheck`: znany residual risk, 16 błędów typowania pandas/GeoPandas zapisane w plan doc;
- lokalny review URL po uruchomieniu serwera: `http://127.0.0.1:8017/lsn-map-options.html`;
- ważne: dostarczony artwork nie jest georeferencjonowanym basemapem GIS; exact lon/lat wymaga MapLibre albo georeferencji/GCP.

Aktualne źródła prawdy:

- `AGENTS.md` - start/handoff po utracie kontekstu;
- `docs/lsn-map-state-and-plan-2026-06-19.md` - backlog, run log, proof ledger, rekomendacja;
- `README.md` / `CLAUDE.md` - działające komendy i guardrails;
- `src/render_lsn_map_options.py` - source of truth dla generowanego HTML.

## Cel główny

Dokończyć zadanie LSN map end-to-end: przygotować klientowi powtarzalny, zweryfikowany prototyp mapy North America / LSN z wariantami Pins, Regions, Flags, Heatmap, Heat + Pins, zoom i fullscreen, a następnie zostawić repo w stanie uporządkowanym, z jasną dokumentacją i bez przypadkowych artefaktów.

Nie zaczynaj dalszej implementacji, dopóki nie wykonasz pełnego rozpoznania aktualnego stanu, nie rozpiszesz backlogu i nie uporządkujesz repo.

## Obowiązkowa kolejność pracy

1. Rozpoznanie aktualnego stanu.
2. Rozpisanie pełnego backlogu i decyzji.
3. Repo cleanup i ustalenie source of truth.
4. Aktualizacja zwartej dokumentacji ciągłej.
5. Dopiero potem implementacja kolejnych zmian.
6. Walidacja, proof i finalny cleanup.

Jeśli którykolwiek wcześniejszy etap jest niejasny albo niespójny, nie przechodź do następnego. Najpierw napraw kontekst.

## Źródła, które trzeba przeczytać na starcie

Przed jakąkolwiek implementacją przeczytaj:

```bash
git status --short --branch
sed -n '1,240p' AGENTS.md
sed -n '1,320p' docs/lsn-map-state-and-plan-2026-06-19.md
sed -n '1,220p' /home/krn/.codex/attachments/397a5685-3b57-4e4c-bd85-bedd091775db/pasted-text-1.txt
```

Traktuj aktualny checkout jako prawdę. Poprzednia rozmowa może pomóc, ale nie jest dowodem.

## Etap 1 - pełne rozpoznanie obecnego stanu

Zanim cokolwiek zmienisz:

- sprawdź `git status --short --branch`;
- sprawdź listę tracked/untracked plików;
- zidentyfikuj, które pliki są źródłami, które są generated output, które są assetami, a które są lokalnym cache/śmieciem;
- sprawdź, jakie HTML-e, screenshoty i dane już istnieją w `data/output/`;
- sprawdź, czy `data/reference/postal_reference.parquet` wpływa na wynik sample run;
- sprawdź obecne komendy z `Makefile`, `README.md`, `CLAUDE.md`;
- uruchom minimalny zestaw walidacji:

```bash
.venv/bin/python -m pytest tests/ -v
.venv/bin/ruff check src/ tests/
.venv/bin/python -m src.run_pipeline --input data/sample/north_america_generator_mapping_template.xlsx --output data/output
pyright src/ tests/
```

Wyniki zapisz z datą w dokumencie planu. Jeśli coś failuje, nie ukrywaj tego i nie claimuj gotowości.

## Etap 2 - pełny backlog i decyzje przed implementacją

Przed kodowaniem rozpisz wszystkie zadania w jednym miejscu: `docs/lsn-map-state-and-plan-2026-06-19.md`.

Backlog musi zawierać minimum:

- zadania data/pipeline,
- zadania renderer/prototype,
- zadania visual QA,
- zadania dokumentacyjne,
- zadania repo cleanup,
- zadania finalnej rekomendacji dla klienta,
- explicit out-of-scope.

Dla każdego zadania zapisz:

- status: `todo`, `in_progress`, `done`, `blocked`, `deferred`;
- krótkie kryterium akceptacji;
- dowód, który potwierdzi wykonanie;
- ryzyko albo zależność, jeśli istnieje.

Nie zaczynaj implementacji, dopóki backlog nie jest spójny i nie rozdziela demo/prototypu od produkcyjnego geokodowania.

## Etap 3 - uporządkowanie repo przed dalszą implementacją

Najpierw posprzątaj repo na poziomie struktury i zasad:

- zdecyduj, które assety mapy mają być commitowane jako źródła demo;
- zostaw `data/output/` jako generated output, chyba że użytkownik jawnie chce commitować artefakty;
- upewnij się, że realne dane klienta i duże referencje nie trafią przypadkowo do gita;
- uporządkuj `.gitignore`;
- usuń lub oznacz przestarzałe dokumentacyjne sprzeczności;
- doprowadź README do zgodności z realnymi komendami, ale dopiero po ustaleniu flow;
- nie usuwaj user-owned dirty changes bez zgody;
- nie rób szerokich refactorów, jeśli nie służą bezpośrednio temu goalowi.

Po cleanupie status repo ma być zrozumiały: każdy tracked/untracked plik ma mieć jasną kategorię i decyzję.

## Etap 4 - zwarta dokumentacja ciągła

Utrzymuj trzy poziomy dokumentacji:

- `GOAL.md` - aktywny cel wykonawczy i kolejność pracy.
- `AGENTS.md` - krótki handoff dla kolejnej sesji: aktualny stan, ryzyka, komendy, next action.
- `docs/lsn-map-state-and-plan-2026-06-19.md` - ledger decyzji, backlog, wyniki walidacji, proof.

Zasady:

- Po każdej istotnej zmianie aktualizuj dokumenty od razu.
- Nie dopisuj wielu rozproszonych notatek, jeśli można zaktualizować istniejące źródło prawdy.
- Jeśli coś się zdezaktualizowało, popraw albo oznacz jako outdated.
- Dokumentacja ma umożliwiać start po utracie context window bez czytania całej rozmowy.
- Nie kończ tury z istotną zmianą w kodzie bez aktualizacji `AGENTS.md` i planu.

## Etap 5 - dopiero teraz implementacja

Po wykonaniu etapów 1-4 możesz zacząć implementację.

Implementuj w tej kolejności:

### 5.1 Jawny tryb referencji danych

Dodać mały mechanizm wyboru referencji:

- `auto` - obecne zachowanie;
- `mock` - wymuś `02_Postal_Reference_MOCK`;
- `parquet` - wymuś realny parquet;
- opcjonalnie `synthetic` - tylko do dev/testów.

Acceptance:

- sample demo może wygenerować 1200/1200 matched w trybie mock;
- real parquet dalej pokazuje prawdziwy match-rate;
- testy pokrywają nowy tryb;
- README wyjaśnia różnicę demo vs production.

### 5.2 Powtarzalny renderer mapy klienta

Dodać `src/render_lsn_map_options.py` albo równoważny moduł.

Renderer ma:

- czytać jawny input CSV/GeoJSON;
- używać domyślnie `data/assets/client-map/new-na-map.svg`, z możliwością podmiany na PNG/SVG przez `--map-image`;
- używać `data/assets/client-map/pin-na-map.svg` przez `--pin-image`;
- generować `data/output/lsn-map-options.html`;
- mieć tryby Pins, Regions, Flags, Heatmap, Heat + Pins;
- mieć osobny Figma renderer `data/output/lsn-map-figma.html` dla komponentu `Map Zoom-In`, jeśli targetem jest aktualny design z Figmy;
- mieć fit i fullscreen;
- mieć panel summary;
- trzymać transform lon/lat -> image space w kodzie;
- jasno oznaczać, że overlay na artworku nie jest precyzyjną basemapą GIS.

Nie edytować ręcznie wygenerowanego HTML jako source of truth.

### 5.3 Komendy i docs

Dodać lub poprawić komendy:

- pipeline demo/mock;
- pipeline production/parquet;
- render map options;
- test/lint/typecheck.

README ma pokazywać tylko komendy, które faktycznie działają.

### 5.4 Visual QA i proof pack

Po wygenerowaniu prototypu:

- sprawdź go w browserze;
- zrób screenshoty 1920x1080 i 1440x900;
- sprawdź tryby Regions, Flags, Heatmap, Hybrid;
- sprawdź fit i fullscreen;
- zapisz proof w jednym katalogu;
- opisz, który proof potwierdza które kryterium.

## Etap 6 - finalna rekomendacja dla klienta

Przygotuj krótką rekomendację:

- Regions: najlepsze do branded overview na niereferencjonowanym artworku;
- Flags: dobre do czytelnej liczby/kraju, ale bardziej dashboardowe;
- heatmapa: dobra do strategicznej gęstości, nie exact lookupu;
- Heat + Pins: dobre do demo, ale nadal overview, nie GIS;
- MapLibre: lepsze, jeśli klient chce precyzyjną mapę operacyjną;
- Leaflet + artwork: lepsze, jeśli klient chce branded sekcję na swojej mapie.
- GCP/georeferencja: potrzebne, jeśli klient chce precyzyjne punkty na tej konkretnej ilustracji.

Nie claimuj finalnej produkcyjnej precyzji bez realnego Excela klienta i walidacji.

## Etap 7 - końcowy cleanup i kryteria ukończenia

Goal jest ukończony dopiero gdy:

- repo ma jasny status i znane decyzje dla wszystkich nowych/zmienionych plików;
- dokumentacja jest aktualna i zwarta;
- pipeline demo i production są rozdzielone;
- generator mapy jest powtarzalny;
- prototyp klienta można odtworzyć jedną komendą;
- visual proof istnieje i został obejrzany;
- `pytest` i `ruff` przechodzą;
- `pyright` przechodzi albo residual risk jest wyraźnie zapisany;
- finalna rekomendacja dla klienta jest gotowa.

## Zakazy

- Nie zaczynaj implementacji przed backlogiem i cleanupem repo.
- Nie commituj realnych danych klienta.
- Nie commituj przypadkowego `data/output/`.
- Nie claimuj 98% geokodowania na podstawie syntetycznego sample.
- Nie buduj WordPress blocka ani React appki przed wyborem kierunku.
- Nie nadpisuj ani nie revertuj cudzych zmian bez zgody.
- Nie twórz kolejnych luźnych dokumentów, jeśli wystarczy aktualizacja `GOAL.md`, `AGENTS.md` albo planu.

## Pierwsza akcja po wznowieniu

Zacznij od rozpoznania i aktualizacji planu, nie od kodowania:

```bash
git status --short --branch
rg --files -g '!data/output/**' -g '!data/reference/**' | sort
sed -n '1,240p' AGENTS.md
sed -n '1,320p' docs/lsn-map-state-and-plan-2026-06-19.md
```

Następnie rozpisz pełny backlog w `docs/lsn-map-state-and-plan-2026-06-19.md`, posprzątaj repo i dopiero wtedy implementuj.
