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

- [ ] smazat `hello.py`
- [ ] `.DS_Store` do `.gitignore` a `git rm --cached .DS_Store`
- [ ] smazat nepoužitou konstantu `N_STARTS`, doplnit docstring do `make_plan`
- [ ] `RESPONSE_WINDOW = 1.5` (rozhodnuto, viz Parametry v `docs/experiment.md`)
- [ ] `# noqa: E402` u importů pod nastavením logování
- [ ] volitelně `.vscode/tasks.json` pro spuštění v Terminálu na macOS

Hotovo když: `uv run ruff check .` projde bez chyb a `git status` je čistý.

## Krok 1: Zapojit no-go start

- [ ] hlavička `run_start(win, lamps, rate, kb, flag, foreperiod, is_nogo)` s typy
- [ ] smazat `random.choice` z `run_start`, prodleva přichází z plánu
- [ ] vlajka se kreslí od prvního snímku okna odpovědi (spolu se zhasnutím)
- [ ] výsledky `commission` a `inhibit`, pořadí podmínek podle `docs/experiment.md`
- [ ] `main()` prochází `make_plan()` a tiskne `foreperiod, is_nogo, result`

Hotovo když: ruční test dá správný výsledek pro go se stiskem, go bez stisku, no-go se stiskem,
no-go bez stisku a stisk před zhasnutím.

## Krok 1b: Rozdělení do modulů a dataclass `Start`

- [ ] moduly v kořeni podle sekce Architektonická rozhodnutí v `CLAUDE.md`
- [ ] `@dataclass Start`, `make_plan()` vrací `list[Start]`, `run_start` dostává jeden `Start`
- [ ] `plan.py` bez importu PsychoPy, první testy v `tests/test_plan.py`, nastavení pytestu v `pyproject.toml`

Hotovo když: program se chová úplně stejně jako po kroku 1 a `uv run pytest` projde.

## Krok 2: Okno pro macOS i Windows

- [ ] **do neděle 15. 11.:** na Windows nainstalovat uv, `git clone`, `uv sync`, spustit a sepsat,
      kde a s jakou chybou to selže (očekávaná první chyba: `import AppKit`)
- [ ] reprodukovat a popsat problém s `fullscr=True` na obou systémech
- [ ] funkce `open_window()` s preferovaným a záložním režimem, bez `AppKit` na úrovni modulu
- [ ] výpis použitého režimu okna, rozlišení a naměřené frekvence

Hotovo když: na Macu i na Windows se okno otevře v popředí přes celou obrazovku
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
