# F1 start pod zátěží

Psychologický experiment do předmětu Kognitivní věda (VŠE FIS). Měří, jestli zátěž pracovní
paměti (zapamatovat si 2 nebo 6 číslic) zhoršuje kontrolu startu v úloze podle startu formule 1:
reakci na zhasnutí semaforu, předčasné starty a starty pod žlutou vlajkou (no-go).

Napsáno v Pythonu s knihovnou [PsychoPy](https://www.psychopy.org/). Běží na macOS
(Apple Silicon) i Windows. Účastník vidí texty česky nebo anglicky.

- **Design experimentu, parametry, formát dat:** [docs/experiment.md](docs/experiment.md)
- **Stav vývoje a historie rozhodnutí:** [docs/roadmap.md](docs/roadmap.md)
- **Test na Windows krok za krokem:** [docs/windows.md](docs/windows.md)

## Vyzkoušení (asi 10 minut)

Díky, že to zkoušíte! Stačí zkrácená verze sezení:

1. Nainstalujte podle sekce [Instalace](#instalace) níže.
2. Displej přepněte na **60 Hz** (MacBook Pro s ProMotion: Nastavení → Monitory → Obnovovací
   frekvence; Windows: Nastavení → Systém → Obrazovka → Upřesnit). Jinak program skončí s hláškou.
3. **macOS:** povolte aplikaci Terminál čtení klávesnice: Nastavení → Soukromí a zabezpečení →
   **Sledování vstupu** (a případně i **Zpřístupnění**) → zapnout Terminál, pak Terminál
   restartovat. Bez toho program na klávesy nereaguje.
4. Spusťte `uv run main.py --short`. Při prvním spuštění program chce **kalibraci velikosti**:
   přiložte platební kartu k šedému obdélníku a šipkami upravte jeho šířku na šířku karty,
   Enter uloží (podněty pak mají na každém displeji stejnou velikost v cm).
5. Nick zadejte jako `test_` + cokoli (ne skutečné jméno), jazyk zvolte klávesou C/E. Projdete
   instrukce, testovací kolo a 4 krátké bloky (asi 6 minut).
6. **Escape** kdykoli ukončí program, závěrečnou obrazovku zavírá také Escape.

**Windows je zatím vyzkoušený jen na jednom počítači a verze s kalibrací velikosti ještě ne.**
Pokud zkoušíte na Windows, postupujte prosím podle [docs/windows.md](docs/windows.md): pomůže
to připravit měření i na Windows.

**Zpětná vazba:** chyby a postřehy (co nefungovalo, co bylo nejasné v instrukcích, jak dlouho
to trvalo) prosím přes [Issues](https://github.com/stepanzuna/f1-start/issues) nebo přímo autorovi.
Data z vyzkoušení zůstávají jen na vašem počítači ve složce `data/test/`.

## Instalace

Potřebujete [uv](https://docs.astral.sh/uv/) (správce Pythonu a balíčků) a git. Správnou verzi
Pythonu (3.11) i PsychoPy nainstaluje `uv sync` sám, přesně podle `uv.lock`.

**macOS** (Terminál):

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
git clone https://github.com/stepanzuna/f1-start.git
cd f1-start
uv sync
```

**Windows** (PowerShell):

```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
git clone https://github.com/stepanzuna/f1-start.git
cd f1-start
uv sync
```

Po instalaci uv zavřete a znovu otevřete terminál, aby našel příkaz `uv`.

## Spuštění

```bash
uv run main.py            # celé sezení (asi 20 minut)
uv run main.py --short    # zkrácené sezení pro test (nick musí začínat „test“)
```

- **macOS:** spouštějte z aplikace Terminál (z terminálu VS Code zůstane okno schované a program
  skončí s hláškou), nebo ve VS Code přes `Cmd+Shift+B`.
- **Windows:** spouštějte z PowerShellu, nebo ve VS Code přes `Ctrl+Shift+B` (otevře nové okno
  PowerShellu).
- Displej musí běžet na **60 Hz** (na MacBooku vypnout ProMotion, na Windows nastavit v Nastavení
  → Obrazovka → Upřesnit). Jinak program skončí s hláškou.
- **Escape** kdykoli ukončí program. Už zapsaná data zůstanou, sezení se označí jako přerušené.

Průběh sezení: kalibrace velikosti (jen poprvé na počítači) → nick účastníka → pořadí bloků
a jazyk (zde `K` = kalibrovat znovu, `V` = ověřit velikost vlajky pravítkem, má 5 × 3 cm)
→ instrukce → testovací kolo (lze opakovat) → 4 bloky po 24 startech, po každém hodnocení
úsilí (Paasova škála) a pauza → zhodnocení.

## Data

Každé sezení uloží do složky `data/` tři soubory se jménem `{nick}_{mac|win}_{datum}_{čas}`:
`.csv` (jeden řádek = jeden start), `_meta.json` (nastavení, seed, hodnocení úsilí, přerušení)
a `_log.txt` (varování PsychoPy). Sloupce a metadata popisuje [docs/experiment.md](docs/experiment.md).

- Nick začínající `pilot` jde do `data/pilot/`, `test` do `data/test/`. Do analýzy se nepočítají.
- `data/machine.json` drží anonymní náhodný identifikátor počítače a jeho kalibraci velikosti.
- **Složka `data/` se nikdy nenahrává na GitHub** (GDPR). Je v `.gitignore` a hlídá to i hook.
- Kontrola dat jednoho sezení: `uv run check_data.py data/<soubor>.csv`
  (bez argumentu zkontroluje nejnovější sezení).

## Vývoj a ověřování

```bash
uv run pytest             # testy čisté logiky (bez okna)
uv run ruff check .       # kontrola stylu
uv run main.py --sim      # simulace celého sezení bez člověka (malé okno, data/sim/)
uv run main.py --sim --short --seed=4242   # rychlá a opakovatelná simulace
```

Simulace „mačká“ klávesy podle scénáře a `check_data.py` pak ověří, že program vyhodnotil
a uložil přesně to, co scénář předpověděl.

Soubory: `config.py` (všechny konstanty a texty), `logic.py` (čistá logika bez PsychoPy),
`simulation.py` (režim simulace), `screens.py` (obrazovky s textem), `main.py` (okno, start,
průběh sezení), `check_data.py` (kontrola dat), `tests/`.

## Pro AI asistenty a další vývojáře

Pravidla, která v projektu platí (ať pracujete ručně, nebo s AI):

- **Parametry experimentu se nemění** (časy, počty, prahy, poměry). Schválené hodnoty jsou
  v `docs/experiment.md` (sekce Parametry) a zamyká je `tests/test_rules.py`. Když tento test
  selže, parametr se změnil bez dohody: neopravujte test, zeptejte se autora.
- **Nic ze složky `data/` nepatří do gitu** (výsledky účastníků, GDPR).
- **Vrstvy souborů:** `main` → `screens` → `simulation` → `logic` → `config`. Nižší vrstva
  neimportuje vyšší; `config.py`, `logic.py` a `simulation.py` neimportují PsychoPy, aby šly
  testovat bez okna. Hlídá to `tests/test_rules.py`.
- **Časování výhradně ve snímcích** (`frames()` a smyčka `draw → win.flip()`), nikdy
  `time.sleep` ani `core.wait`; klávesnice (iohub) se čte v každém snímku a Escape vždy ukončí.
- **Před každou změnou a po ní:** `uv run pytest`, `uv run ruff check .` a simulace
  `uv run main.py --sim --short`, výsledek ověřit `uv run check_data.py`.
- Konstanty a všechny texty pro účastníka (česky i anglicky) jsou v `config.py`.
  Návrh a zdůvodnění rozhodnutí jsou v `docs/experiment.md` a v logu `docs/roadmap.md`.
