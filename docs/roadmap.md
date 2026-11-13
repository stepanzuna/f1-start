# Roadmapa

Pravidla: jeden krok najednou. Po dokončení kroku odškrtnout, doplnit řádek do logu dole
a commitnout. Každý krok má „Hotovo když“: bez splnění se nepokračuje.

## Hotovo

- [x] projekt přes `uv`, Python 3.11, PsychoPy, soukromý repozitář na GitHubu
- [x] semafor časovaný ve snímcích (`frames`, `make_lamps`, `draw_lamps`)
- [x] měření startu přes iohub: `jump_start` / `anticipation` / `go` / `omission`
- [x] pauza mezi starty, Escape kdykoli, kontrola `rate is None`
- [x] `make_plan()`: vyvážený plán prodlev × go/no-go, zamíchaný
- [x] `make_flag()`: žlutá vlajka (zatím se nekreslí)

## Krok 0: Úklid repozitáře

- [x] smazat `hello.py`
- [x] `.DS_Store` do `.gitignore` a `git rm --cached src/.DS_Store`
- [x] doplnit docstring do `make_plan` (smazání `N_STARTS` přesunuto do kroku 1)
- [x] `RESPONSE_WINDOW = 1.5` (rozhodnuto, viz Parametry v `docs/experiment.md`)
- [x] `# noqa: E402` u importů pod nastavením logování, E402 zapnuté v `pyproject.toml`
- [x] smazat šablonu balíčku (`src/`, `[project.scripts]`, `[build-system]`)
- [x] `.vscode/tasks.json` pro spuštění v Terminálu na macOS (`Cmd+Shift+B`)

Hotovo když: `uv run ruff check .` projde bez chyb a `git status` je čistý.

## Krok 1: Zapojit no-go start

- [x] hlavička `run_start(win, lamps, rate, kb, flag, foreperiod, is_nogo)` s typy
- [x] smazat `random.choice` z `run_start`, prodleva přichází z plánu
- [x] vlajka se kreslí od prvního snímku okna odpovědi (spolu se zhasnutím)
- [x] výsledky `commission` a `inhibit`, pořadí podmínek podle `docs/experiment.md`
- [x] `main()` prochází `make_plan()` a tiskne `foreperiod, is_nogo, result`
- [x] smazat konstantu `N_STARTS` (nahradí ji plán)

Hotovo když: ruční test dá správný výsledek pro go se stiskem, go bez stisku, no-go se stiskem,
no-go bez stisku a stisk před zhasnutím.

## Krok 1b: Rozdělení do souborů a dataclass `Start`

- [x] `config.py` se všemi konstantami, čísla lamp a vlajky převedená na konstanty
- [x] `logic.py`: `@dataclass Start`, `make_plan()` vrací `list[Start]` (zástupné hodnoty
      `load="none"`, `block=0`, `set_index=0`, `start_in_set=0` do kroku 7)
- [x] `run_start` dostává jeden `Start`, `import AppKit` uvnitř `main()`
- [x] `logic.py` bez importu PsychoPy, první testy v `tests/test_logic.py`, nastavení pytestu v `pyproject.toml`

Hotovo když: program se chová úplně stejně jako po kroku 1 a `uv run pytest` projde.

## Krok 2: Okno (kód pro oba systémy, ověření na macOS)

- [x] funkce `open_window()` s režimy `fullscr` a `borderless` (`WINDOW_MODE` v `config.py`),
      kód jen pro macOS ve větvi `sys.platform == "darwin"`, bez `AppKit` na úrovni modulu
- [x] diagnostické výpisy (vytváření okna, měření frekvence), vypadlé snímky po každém startu
- [x] reprodukovat a popsat problém s `fullscr=True` na macOS (Terminál, `Cmd+Shift+B`, terminál VS Code)
- [x] rozhodnout výchozí režim, úklid výpisů, výpis režimu okna, rozlišení a frekvence

Hotovo když: na Macu se okno otevře v popředí přes celou obrazovku
a 5 testovacích startů proběhne bez vypadlých snímků.

## Krok 2u: Velikost podnětů ve stupních zrakového úhlu

- [ ] změřit šířku obrazovky v cm (MacBook, později Windows), vzdálenost 60 cm
- [ ] `monitors.Monitor` pro každý počítač, okno s `units="deg"`
- [ ] převést rozměry lamp a vlajky na stupně (nové hodnoty schválit, zapsat do `docs/experiment.md`)

Hotovo když: lampy a vlajka mají na Macu stejnou fyzickou velikost, jakou předpovídá výpočet
ze stupňů, a zmizí varování „Monitor specification not found“.

## Krok 2w: Ověření na Windows (později, před pilotem)

- [ ] na Windows nainstalovat uv, `git clone`, `uv sync`, spustit a sepsat, kde a s jakou chybou to selže
- [ ] zjistit rozlišení, škálování displeje (DPI) a obnovovací frekvenci
- [ ] oba režimy okna z PowerShellu i z terminálu VS Code, skutečná velikost okna v pixelech

Hotovo když: na Windows se okno otevře v popředí přes celou obrazovku
a 5 testovacích startů proběhne bez vypadlých snímků.

## Krok 3: Ukládání do CSV a metadat

- [ ] složka `data/` (v `.gitignore`), název souboru podle `docs/experiment.md`
- [ ] sloupce CSV podle `docs/experiment.md`, `rt_ms` zaokrouhlené, `flush()` po každém zápisu
- [ ] `…_meta.json` se vším ze specifikace, `aborted = True` při Escape
- [ ] počítání vypadlých snímků na start

Hotovo když: po běhu existuje CSV i meta, Escape uprostřed neztratí už uložená data
a `git status` data neukazuje.

## Krok 4: Úvodní obrazovka s nickem

- [ ] znovupoužitelná funkce pro textový vstup v okně (Enter potvrdí, Backspace maže)
- [ ] validace nicku a kontrola, jestli už v `data/` existuje
- [ ] automatické přiřazení pořadí bloků (střídání na tomto počítači), zobrazení a přepsání klávesou A/B
- [ ] nick začínající `pilot` ukládat do `data/pilot/`

Hotovo když: nick se objeví v názvu CSV i ve sloupci `participant`, neplatný nick program odmítne
a dvě dokončená sezení po sobě dostanou opačné pořadí bloků.

## Krok 5: Zpětná vazba v pauze

- [ ] texty podle `docs/experiment.md`, stejné ve všech podmínkách

Hotovo když: po každém startu se zobrazí správná hláška.

## Krok 6: Paměťová zátěž

- [ ] zobrazení číslic (2 nebo 6), sada 3 startů, vybavení přes funkci z kroku 4
- [ ] sloupce `digits_shown`, `digits_typed`, `recall_correct`, zápis CSV po sadě

Hotovo když: celá sada proběhne a v CSV jsou 3 řádky se správnými číslicemi.

## Krok 7: Plán celého sezení

- [ ] plán na podmínku (9 go + 3 no-go na prodlevu), max 2 no-go za sebou
- [ ] rozdělení do bloků ABBA/BAAB, `random.Random(seed)`, seed do metadat
- [ ] testy v `tests/` přes pytest: počty, poměr, pravidlo max 2 no-go, stejný seed = stejný plán

Hotovo když: `uv run pytest` projde a plán sezení má 96 startů ve 4 blocích.

## Krok 8: Testovací kolo

- [ ] 4 starty bez číslic (1 no-go) + 1 sada s 2 číslicemi, `phase = "practice"`
- [ ] `R` = zopakovat, mezerník = pokračovat

Hotovo když: testovací kolo jde zopakovat a v CSV je odlišené od ostré části.

## Krok 9: Instrukce a průběh sezení

- [ ] úvodní instrukce, Paasova škála po bloku, pauza mezi bloky, závěrečná obrazovka

Hotovo když: celé sezení proběhne od nicku po poděkování bez zásahu do kódu.

## Krok 10: Pilot

- [ ] 2–3 lidé, na Macu i na Windows
- [ ] kontrola délky sezení, přesnosti číslic (cíl 70–90 %), no-go chybovosti, vypadlých snímků
- [ ] data z pilotu se do analýzy nezahrnují

## Log

- 2026-11-10: semafor, měření startu, pauza, Escape, `make_plan`, vlajka vytvořená.
- 2026-11-12: architektonická rozhodnutí: moduly po kroku 1, `dataclass Start`, plán a data bez
  PsychoPy, Windows pro sběr dat, automatické střídání pořadí bloků na každém počítači zvlášť.
- 2026-11-12: parametry: interval lamp 1,0 s, okno odpovědi 1,5 s, vlajka 500 × 300 px,
  zpětná vazba s ms, testovací kolo 4 starty + 1 sada, Paasova škála po bloku.
- 2026-11-12: krok 0: úklid (`hello.py`, `src/`, šablona balíčku), `RESPONSE_WINDOW = 1.5`,
  E402 v ruffu, `tasks.json`; `make_flag`, `make_plan`, `jump_start`, lampy na y = −90.
- 2026-11-12: krok 1: no-go start se žlutou vlajkou, výsledky `commission` a `inhibit`,
  `main()` prochází `make_plan()`; ruční test ověřil všech 5 případů.
- 2026-11-13: rozhodnutí: tři soubory (`config.py`, `logic.py`, `main.py`) místo sedmi modulů.
- 2026-11-13: krok 1b: `config.py` (i rozměry lamp a vlajky), `logic.py` s `@dataclass Start`
  a `make_plan()`, `run_start` dostává `Start`, `AppKit` uvnitř `main()`, první testy pytestem.
- 2026-11-13: krok 2: `open_window(mode)` (`fullscr` / `borderless`, AppKit jen ve větvi darwin),
  kontrola frekvence 60 ± 1 Hz, pojistka proti spuštění z terminálu VS Code; na macOS `fullscr`
  z Terminálu a `Cmd+Shift+B` bez vypadlých snímků ve startech. Windows přesunuto do kroku 2w,
  nový krok 2u (jednotky `deg`, Retina).
