# Roadmapa

Pravidla: jeden krok najednou, provádí se podle skillu `/krok`. Po dokončení kroku odškrtnout,
doplnit řádek do logu dole a commitnout na větev kroku. Každý krok má „Hotovo když“: bez splnění
se nepokračuje. Položky označené (ručně) ověřuje uživatel, ostatní Claude sám.

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

## Krok 3: Ukládání do CSV a metadat

- [x] složka `data/` (v `.gitignore`), název souboru podle `docs/experiment.md`
- [x] sloupce CSV podle `docs/experiment.md`, `rt_ms` zaokrouhlené, `flush()` po každém zápisu
- [x] počítání vypadlých snímků na start
- [x] kontrola existence souboru **před** otevřením okna (dnes druhé spuštění ve stejné minutě
      spadne s `FileExistsError` až s otevřeným oknem)
- [x] `…_meta.json` se vším ze specifikace: zápis hned po změření frekvence s `aborted = true`,
      přepis na konci sezení (`aborted = false`, konec, vypadlé snímky celkem)
- [x] log `…_log.txt` s varováními PsychoPy (limit varování o vypadlých snímcích zvýšen z 5)
- [x] `check_data.py`: kontrola CSV a meta jednoho sezení (sloupce, hodnoty `outcome`, `rt_ms`
      jen u výsledků s reakcí, počet řádků proti plánu, vypadlé snímky, `aborted`)
- [x] `tests/test_rules.py`: zakázaná volání a importy ve zdrojácích, zámek schválených parametrů
- [x] (ručně) celý běh a jeden běh přerušený Escapem

Hotovo když: po běhu existuje CSV, meta i log, `check_data.py` je projde bez chyb, Escape
uprostřed neztratí už uložená data a meta má `aborted = true`, `git status` data neukazuje.

## Krok 3s: Režim simulace

- [x] `uv run main.py --sim`: falešná klávesnice se stejným rozhraním jako iohub (`getKeys`,
      `clearEvents`, `clock`), stisky podle scénáře (všechny typy výsledků), menší okno
      (`windowed`, jen pro simulaci, místo původně plánovaného `borderless` přes celou obrazovku)
- [x] data do `data/sim/`, `simulated = true` v meta, nikdy do střídání pořadí bloků
- [x] test, že simulace vyrobí všech 6 typů výsledků a `check_data.py` je projde
- [x] `classify_press` v `logic.py` (vyhodnocení stisku testovatelné bez okna)
- [x] `--sim-escape` (přerušení Escapem), neznámý argument ukončí program,
      `check_data.py` porovná simulaci se scénářem a hlídá klávesnici a okno ostrých sezení

Hotovo když: Claude spustí simulaci sám z terminálu VS Code a `check_data.py` výstup projde.
Simulace neověřuje časování, to dál ověřuje ruční test.

## Krok 2w: Ověření na Windows (co nejdřív, jakmile bude Windows k dispozici)

Riziko: kdyby se na Windows opakovaly potíže s celou obrazovkou jako na Macu, oprava potřebuje
čas. Proto hned po kroku 3, ne až před pilotem. Výsledky (meta a log z běhu s nickem `test`,
bez osobních údajů) zkopírovat do `docs/diag/` a commitnout, Claude je pak přečte.

- [ ] (ručně) na Windows nainstalovat uv, `git clone`, `uv sync`, spustit a sepsat, kde a s jakou chybou to selže
- [ ] zjistit rozlišení, škálování displeje (DPI) a obnovovací frekvenci
- [ ] (ručně) oba režimy okna z PowerShellu i z terminálu VS Code, skutečná velikost okna v pixelech
- [ ] (ručně) porovnat fyzickou velikost lamp a vlajky s Macem (pravítkem; Mac: vlajka 5 × 3 cm).
      Při velkém rozdílu rozhodnout: přijmout (počítač je faktor), nebo jednotky `deg`
      (`monitors.Monitor` s šířkou displeje v cm a vzdáleností 60 cm, na Retině
      `win.monitor.setSizePix(win.size)`; varování „Monitor specification not found“ zůstane)

Hotovo když: na Windows se okno otevře v popředí přes celou obrazovku
a 5 testovacích startů proběhne bez vypadlých snímků.

## Krok 4: Úvodní obrazovka s nickem

- [x] znovupoužitelná funkce pro textový vstup v okně (Enter potvrdí, Backspace maže;
      `edit_text` a `nick_input_key` v `logic.py`, znaky z `KeyPress.code`)
- [x] validace nicku a kontrola, jestli už v `data/` existuje (Enter = přesto pokračovat,
      Backspace = opravit)
- [x] automatické přiřazení pořadí bloků (střídání na tomto počítači), zobrazení a přepsání klávesou A/B
- [x] volba jazyka účastníka (C/E), `language` v meta, texty pro účastníka česky i anglicky v `TEXTS`
- [x] simulace napíše nick (s chybou a Backspace) a přepne jazyk, `check_data.py` to ověří
- [x] nick začínající `pilot` ukládat do `data/pilot/`, `test` do `data/test/`, obojí mimo střídání
- [x] (ručně) psaní nicku na skutečné klávesnici, obě obrazovky, dvě dokončená sezení po sobě

Hotovo když: nick se objeví v názvu CSV i ve sloupci `participant`, neplatný nick program odmítne
a dvě dokončená sezení po sobě dostanou opačné pořadí bloků.

## Krok 5: Zpětná vazba v pauze

- [x] texty podle `docs/experiment.md`, stejné ve všech podmínkách, ve zvoleném jazyce
      (`feedback_text` v `logic.py`, hláška nad lampami)
- [x] simulace uloží obrázek první pauzy po každém výsledku do `data/sim/…_screens/`
- [x] (ručně) hlášky česky i anglicky, čitelnost a umístění na celé obrazovce

Hotovo když: po každém startu se zobrazí správná hláška.

## Krok 6: Paměťová zátěž

- [x] zobrazení číslic (2 nebo 6), sada 3 startů, vybavení přes funkci z kroku 4
      (pravidla v `docs/experiment.md`, „Číslice a vybavení“)
- [x] sloupce `digits_shown`, `digits_typed`, `recall_correct`, zápis CSV po sadě
- [x] dočasně do kroku 7: testovací plán rozdělený do sad, zátěž se střídá nízká/vysoká
- [x] simulace píše odpovědi (správně, špatně, opraveno, kratší), `check_data.py` je ověří
- [x] (ručně) číslice a vybavení na celé obrazovce, česká klávesnice

Hotovo když: celá sada proběhne a v CSV jsou 3 řádky se správnými číslicemi.

## Krok 7: Plán celého sezení

- [x] plán na podmínku (9 go + 3 no-go na prodlevu), rozdělení do bloků po 6 startech
      na prodlevu (2× 2 no-go + 2× 1 no-go), max 2 no-go za sebou v bloku, číslice do plánu
- [x] rozdělení do bloků ABBA/BAAB, `random.Random(seed)`, seed do metadat
- [x] ostré starty mají `block` 1–4 (jinak by `make_row` dal `phase = "practice"`),
      `set_index` a `start_in_set` skutečné hodnoty; `check_data.py` přegeneruje plán ze seedu
      a porovná ho s CSV (pokryje i velikost sady a zátěž)
- [x] nahradit dočasné `assign_sets` (krok 6) a `random.Random()` bez seedu v `main.py`
- [x] testy v `tests/` přes pytest: počty, poměr, pravidlo max 2 no-go, stejný seed = stejný plán
- [x] zkrácený plán `--short` pro testy (12 startů), `short` v meta
- [x] (ručně) zkrácené sezení přes celou obrazovku, přechody mezi bloky

Hotovo když: `uv run pytest` projde a plán sezení má 96 startů ve 4 blocích.

## Krok 8: Testovací kolo

- [x] 4 starty bez číslic (1 no-go) + 1 sada s 2 číslicemi, `phase = "practice"`
- [x] `R` = zopakovat, mezerník = pokračovat (obrazovka čte bez `keyList`, viz CLAUDE.md)
- [x] zpětná vazba k vybavení v testovacím kole, průběh sad v `run_sets` (sdílí ostrá část)
- [x] `check_data.py` přegeneruje testovací kola ze seedu, přesný počet řádků před Escapem
- [x] opakované testovací kolo: číslice podle klíče (blok, sada) se nesmí opakovat, část 1
      (bez číslic) se zapisuje po každém startu a nesmí se slít do jedné sady; upravit vzorec
      Escapu v `check_simulation` pro sady různé délky
- [x] (ručně) testovací kolo, opakování, vypadlý snímek po prvním stisku v testovacím kole
- [x] úvodní obrazovka testovacího kola (na žádost uživatele), obecná `ask_key`
- [ ] ověřit, že vypadlý snímek po prvním stisku v sezení padne do testovacího kola,
      ne do prvního ostrého startu (`check_data.py` ho hlásí jako varování)

Hotovo když: testovací kolo jde zopakovat a v CSV je odlišené od ostré části.

## Krok 9: Instrukce a průběh sezení

- [x] texty instrukcí sepsat do `docs/experiment.md` (česky i anglicky, generované z `config.py`)
- [ ] (ručně) schválit texty („Texty ke schválení (krok 9)“ v `docs/experiment.md`)
- [x] úvodní instrukce, Paasova škála po bloku, pauza mezi bloky, závěrečná obrazovka
- [x] předěl „Teď si vyzkoušíte sadu s číslicemi“ v testovacím kole, začátek měření
- [x] závěrečné zhodnocení (`session_summary`) po uložení dat, hodnocení úsilí do meta po bloku
- [x] simulace projde celé sezení, `check_data.py` hlídá hodnocení úsilí
- [ ] (ručně) zkrácené sezení od nicku po závěr

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
- 2026-11-13: krok 2u zrušen: jednotky zůstávají `pix` (na Macu velikost v pořádku),
  porovnání velikosti s Windows přesunuto do kroku 2w.
- 2026-11-13: samostatný režim práce s Claude Code: celé kroky bez průběžného schvalování,
  hooky (ruff po úpravě, ruff + pytest na konci, blokace `data/` v gitu), skill `/krok`,
  subagent `spec-reviewer`, otevřené otázky ke krokům 4–9 v `docs/experiment.md`.
  Schváleno: `check_data.py`, režim simulace (nový krok 3s), meta s `aborted = true` od začátku,
  krok 2w hned po kroku 3. Historie okna přesunuta z `CLAUDE.md` do tohoto logu:
  dřív `fullscr` z terminálu VS Code zůstalo za VS Code (nepomohlo ani `winHandle.activate()`),
  pak se `fullscr` neotevřelo a program visel, proto dočasně okno velikosti displeje + `AppKit`
  na úrovni `main()` (na Windows by spadlo, okno přes kompozitor = horší časování);
  vyřešeno v kroku 2 přes `open_window(mode)`, zamrznutí se už neopakovalo.
- 2026-11-13: krok 3 hotový: meta (`aborted = true` od začátku, přepis na konci), log s varováními
  PsychoPy (i důvod ukončení při špatné frekvenci), kontrola kolize názvu před oknem, kontrola
  backendu klávesnice, `check_data.py`, `tests/test_rules.py`. Ruční test: celý běh (16 startů,
  všech 6 typů výsledků mimo anticipation) a 2 přerušené běhy, `check_data.py` vše prošlo,
  kolize názvu ověřena bez okna. Vypadlý snímek po prvním stisku se teď počítá do startu 1
  (v ostrém sezení ho pohltí testovací kolo, ověří krok 8).
- 2026-11-13: všech 15 otevřených otázek rozhodnuto podle návrhu a zapsáno do `docs/experiment.md`
  (číslice bez opakování, vybavení bez limitu, rozdělení bloků po 6 startech na prodlevu, vykání,
  Paasova škála, `data/test/` mimo střídání aj.).
- 2026-11-13: krok 3s hotový: `uv run main.py --sim` / `--sim-escape`, `SimulatedKeyboard`
  a scénář v `logic.py`, `classify_press` vytažené z `run_start`, okno simulace menší (jen pro
  simulaci, velikost podle podnětů a Retiny), `check_data.py` porovná simulaci se scénářem
  a hlídá klávesnici a okno ostrých sezení, neznámý argument ukončí program. Ověřeno 3 běhy
  simulace (celá, s Escapem, po opravě okna), vše bez vypadlých snímků; recenze spec-reviewer
  zapracovaná.
- 2026-11-13: krok 4 hotový: obrazovka s nickem (ověření, varování u existujícího nicku, filtr
  fantomových stisků po Shiftu), obrazovka nastavení (pořadí bloků A/B, jazyk C/E, cílová složka),
  texty pro účastníka česky i anglicky v `TEXTS` (rozhodnutí: volba jazyka, ne oba naráz),
  `language` v meta, `pilot…`/`test…` do podsložek mimo střídání. Ruční test: `test_x` bez
  fantomu do `data/test/`, EN; `zkouska1` dvakrát dokončeno → ABBA, pak BAAB, třetí sezení
  ukázalo ABBA podle 2 sezení. Testovací soubory přesunuty do `data/test/`. Neověřeno ručně:
  přepsání pořadí klávesou A/B (pokryto testem).
- 2026-11-13: krok 5 hotový: hláška v pauze podle výsledku ve zvoleném jazyce (`feedback_text`),
  nad lampami (y = 60 px, písmo 60 px). Ruční test v češtině (8 startů, 4 typy hlášek) bez
  vypadlých snímků, uživatel bez připomínek; angličtina ověřena obrázky ze simulace.
- 2026-11-13: krok 6 hotový: sada = číslice 2 s + 0,5 s prázdno, 3 starty, vybavení (jen číslice,
  česká horní řada i Caps Lock, Backspace, Enter i u kratší odpovědi), zápis CSV po sadě, číslice
  ve slovníku podle (blok, sada). Dočasně do kroku 7 sady se střídající zátěží. Ruční test: 3 celé
  sady (2 a 6 číslic) správně uložené, Escape ve 4. sadě ji nezapsal, bez vypadlých snímků.
  Simulace s Escapem uprostřed sady ověřena.
- 2026-11-13: krok 7 hotový: plán 96 startů ve 4 blocích ABBA/BAAB ze seedu (9 go + 3 no-go
  na prodlevu a podmínku, blok 6× každá prodleva s 2×2 a 2×1 no-go, max 2 no-go za sebou,
  8 sad po 3), seed a `short` v meta, `check_data.py` přegeneruje plán a porovná s CSV,
  zkrácený plán `--short` jen pro simulaci a `test…`. Simulace celého sezení 11:41 min.
  Ruční test: zkrácené sezení v pořádku, `--short` s ostrým nickem odmítnut.
- 2026-11-13: parametr změněn na žádost uživatele po ručním testu: `DIGITS_DURATION` 2 s → 4 s
  pro obě zátěže (6 číslic za 2 s nešlo zapamatovat; stejný čas, aby se podmínky lišily jen
  počtem číslic). Odhad délky ostré části asi 15–16 min.
- 2026-11-14: krok 8 hotový: testovací kolo (4 starty bez číslic + sada se 2 číslicemi a hláškou
  ke správnosti vybavení), úvodní obrazovka, R = zopakovat / mezerník = pokračovat, kola ze seedu
  vlastním generátorem, `check_data.py` je přegeneruje. Ruční test: 2 kola, opakování, přechod
  do ostré části v pořádku; vypadlý snímek po prvním stisku se tentokrát neobjevil vůbec.
  Uživatel potvrdil: v ostré části bez zpětné vazby k vybavení; navrhl celkové zhodnocení
  na konci sezení (otázka 5, krok 9). Otázky 1–4 ke kroku 8 implementovány podle návrhu.
- 2026-11-14: refaktorizace po dohodě (před krokem 9): obrazovky z `main.py` do `screens.py`,
  simulace z `logic.py` do `simulation.py` (přesun beze změny kódu, 83 definic shodných znak po
  znaku), `main()` rozdělená na fáze, `run_set`. Ověřeno simulací s pevným seedem (`--seed=N`,
  jen se simulací): data, meta i obrázky obrazovek shodné pixel po pixelu, plný běh i s Escapem.
  Test pravidel hlídá vrstvy importů a načtení PsychoPy až po ztišení logování.
