# Experiment: F1 start pod zátěží

## Kontext

- Předmět Kognitivní věda, VŠE FIS. Semestrální projekt formou experimentu, odevzdání do
  13. týdne semestru (zhruba polovina prosince 2026), obhajoba u ústní zkoušky.
- Sběr dat začátkem prosince, cíl 30 účastníků (nábor asi 34 s rezervou na vyřazení).
- Měří se na MacBooku Pro a případně souběžně na jednom počítači s Windows.

## Výzkumná otázka a hypotézy

Zhoršuje zátěž pracovní paměti inhibiční kontrolu (nestartovat předčasně ani pod vlajkou)
a časovou přípravu na očekávaný podnět?

- **H1:** při vysoké zátěži víc `commission` (start pod žlutou vlajkou).
- **H2:** při vysoké zátěži víc `jump_start` (stisk před zhasnutím).
- **H3:** při vysoké zátěži delší a proměnlivější reakční časy v go startech.
- **H4 (exploratorní):** efekt délky prodlevy (foreperiod effect) je při vysoké zátěži slabší.

## Design

- Uvnitř subjektů. Jediný faktor: zátěž pracovní paměti, **nízká = 2 číslice**, **vysoká = 6 číslic**.
- 4 bloky v pořadí ABBA nebo BAAB (A = nízká, B = vysoká). Pořadí se přiřazuje automaticky,
  střídáním na každém počítači zvlášť (viz Úvodní obrazovka).
- Jedna paměťová sada = **3 starty**. Na podmínku 48 startů = 16 sad. Blok = 24 startů = 8 sad.
- Celkem 96 startů + testovací kolo. Cíl: sezení do 20–25 minut.

## Průběh jedné sady

1. Zobrazení číslic na 2 s, pak 0,5 s prázdná obrazovka.
2. Třikrát start:
   - lampy 1–4 se rozsvěcují po 1,0 s (`LIGHT_INTERVAL`),
   - pak se rozsvítí lampa 5 a svítí **přesně po dobu prodlevy** (`FOREPERIODS` = 0.5 / 1.25 / 2.0 / 2.75 s),
   - zhasnutí; u no-go startu se **ve stejném snímku** objeví žlutá vlajka (obdélník nad lampami),
   - okno odpovědi 1,5 s (`RESPONSE_WINDOW`), odpověď mezerníkem,
   - pauza 1,0 s (`REST_INTERVAL`), během ní zpětná vazba.
3. Vybavení: účastník napíše číslice a potvrdí Enterem.

Po každém bloku: hodnocení vnímané námahy na Paasově škále 1–9 a krátká pauza.

## Plán startů

- Na každou podmínku: každá prodleva 9× go a 3× no-go (25 % no-go). Plán se vygeneruje
  systematicky smyčkami a pak zamíchá.
- Nejvýš 2 no-go starty za sebou: zamíchat, zkontrolovat, případně míchat znovu.
- Plán podmínky (48 startů) se rozdělí do jejích dvou bloků po 24 startech.
- Náhoda přes `random.Random(seed)`, seed se ukládá do metadat.
- Teď pro testování: `GO_PER_FOREPERIOD = 3`, `NOGO_PER_FOREPERIOD = 1` (16 startů).

## Výsledky startu

| outcome        | kdy                                                    | rt     |
|----------------|--------------------------------------------------------|--------|
| `jump_start`   | stisk před zhasnutím (i `rt < 0` v prvním snímku okna) | `None` |
| `anticipation` | go start, stisk dřív než `ANTICIPATION_THRESHOLD` (0,1 s) | ano |
| `go`           | go start, normální reakce                              | ano    |
| `omission`     | go start, bez stisku do konce okna                     | `None` |
| `commission`   | no-go start, jakýkoli stisk po zhasnutí                | ano    |
| `inhibit`      | no-go start, bez stisku do konce okna                  | `None` |

Pořadí vyhodnocení stisku v okně odpovědi: `rt < 0` → `jump_start`; no-go → `commission`;
`rt < ANTICIPATION_THRESHOLD` → `anticipation`; jinak `go`.

## Zpětná vazba v pauze (stejná ve všech podmínkách)

- `go`: „Reakce 213 ms“
- `jump_start`, `anticipation`: „Předčasný start!“
- `commission`: „Start pod žlutou vlajkou!“
- `inhibit`: „Správně, bez startu“
- `omission`: „Bez reakce“

## Úvodní obrazovka a nick

- Experimentátor zadá nick účastníka přímo v okně PsychoPy. Doporučení: textový vstup napsat
  jako vlastní funkci (čtení kláves v každém snímku), protože stejný mechanismus poslouží
  i pro vybavení číslic. Názvy kláves z iohub nejdřív ověř výpisem.
- Nick: malá písmena a–z, číslice, `-` a `_`, délka 2–16 znaků. Nesmí to být skutečné jméno.
- Pokud v `data/` už existuje soubor se stejným nickem, upozornit a chtít jiný nick nebo potvrzení.
- Pořadí bloků: program spočítá dokončená ostrá sezení v `data/` na tomto počítači
  (meta s `aborted = False`, bez pilotu). Sudý počet → ABBA, lichý → BAAB. Úvodní obrazovka
  přiřazené pořadí ukáže a experimentátor ho může klávesou A/B přepsat.
- Pilotní sezení: nick začínající `pilot` se ukládá do `data/pilot/` a do střídání se nepočítá.

## Testovací kolo

- Po zadání nicku a instrukcích, před ostrou částí.
- Část 1: 4 starty bez číslic, každý s jinou prodlevou, z toho 1 no-go.
  Část 2: 1 sada (3 starty) s 2 číslicemi.
- Zpětná vazba stejná jako v ostré části.
- Na konci: `R` = zopakovat testovací kolo, mezerník = pokračovat do ostré části.
- Ukládá se do stejného CSV se sloupcem `phase = "practice"`.

## Data

Soubor `data/{nick}_{stroj}_{YYYY-MM-DD_HHMM}.csv`, kde `stroj` je `mac` nebo `win`
podle `sys.platform` (jméno počítače se na macOS mění podle sítě, nepoužívat).
Složka `data/` je v `.gitignore`.

Zápis: po každé sadě (3 řádky po vybavení číslic) a hned `flush()`, aby Escape ani pád
neztratily dřívější data. V části testovacího kola bez číslic po každém startu.

Sloupce CSV (jeden řádek = jeden start):

| sloupec | význam |
|---|---|
| `participant` | nick |
| `machine` | `mac` / `win` |
| `phase` | `practice` / `main` |
| `block` | 0 pro testovací kolo, jinak 1–4 |
| `load` | `none` / `low` / `high` |
| `set_index` | pořadí sady v bloku |
| `start_in_set` | 1–3 |
| `trial_index` | pořadí startu v celém sezení |
| `foreperiod_s` | prodleva v sekundách |
| `is_nogo` | `True` / `False` |
| `outcome` | výsledek podle tabulky výše |
| `rt_ms` | reakční čas v ms na 1 desetinné místo, prázdné pro `None` |
| `digits_shown` | zobrazené číslice (jako text, aby se neztratily úvodní nuly) |
| `digits_typed` | napsané číslice |
| `recall_correct` | `True` / `False` |
| `dropped_frames` | vypadlé snímky během startu |
| `timestamp` | čas zápisu (ISO 8601) |

Metadata `…_meta.json`: nick, stroj, `platform.platform()`, verze Pythonu a PsychoPy,
git commit (`git rev-parse --short HEAD`), začátek a konec sezení, `aborted` (Escape),
pořadí bloků, seed, naměřená frekvence, režim okna, backend klávesnice,
kopie všech časových konstant, hodnocení námahy po blocích, vypadlé snímky celkem.
Doplněno 13. 11. 2026: skutečná velikost okna v px, `simulated` (režim simulace),
`planned_starts` (počet startů v plánu sezení), u git commitu přípona `-dirty`, když běžel
kód s necommitnutými změnami. `keyboard_backend` je backend, který PsychoPy skutečně použil;
když to není `iohub`, program skončí ještě před otevřením okna.

Meta se zapíše hned po změření frekvence s `aborted = true` a `ended_at = null`. Na řádném konci
sezení se přepíše (`aborted = false`, konec, vypadlé snímky celkem). Přerušené sezení tak má
vždy `aborted = true`, ať skončilo Escapem, pádem programu, nebo vypnutím počítače.

Log `…_log.txt`: varování PsychoPy během sezení (hlavně vypadlé snímky `t of last frame was …ms`),
pro kontrolu kvality měření.

Simulace (`uv run main.py --sim`) ukládá do `data/sim/` a do střídání pořadí bloků
ani do analýzy se nepočítá.

## Otevřené otázky (k rozhodnutí, sepsáno 13. 11. 2026)

Ke každé je návrh. Stačí odpovědět „návrh ok“ nebo napsat jinak. Po rozhodnutí se otázka
přesune do příslušné sekce výše a tady se smaže.

**Krok 4 (úvodní obrazovka)**
1. Nick už v `data/` existuje: *návrh:* hláška „Nick už existuje. Enter = přesto pokračovat,
   Backspace = opravit“. Nový soubor má jiný čas v názvu, nic se nepřepíše.
1b. Testovací běhy během vývoje (dnes zástupný nick `test`) by se počítaly do střídání pořadí
   bloků. *Návrh:* nick začínající `test` ukládat do `data/test/` a do střídání nepočítat
   (stejně jako `pilot`). Do té doby: před sběrem dat smazat `data/test_*`.

**Krok 6 (paměťová zátěž)**
2. Jak se generují číslice: *návrh:* náhodně 0–9 **bez opakování** v rámci sady, nula smí být
   první. Generují se předem v plánu sezení (stejný seed = stejné číslice).
3. Zobrazení: *návrh:* všechny číslice najednou uprostřed, oddělené mezerou („4 7 1 9 0 3“),
   bílé písmo, výška 80 px.
4. Vybavení: *návrh:* bez časového limitu; přijímá jen číslice 0–9, nejvýš tolik, kolik jich
   bylo zobrazeno; Enter potvrdí i kratší odpověď. `recall_correct = True` jen při přesné shodě
   včetně pořadí.
5. Zpětná vazba k vybavení: *návrh:* v ostré části žádná (stejné ve všech podmínkách),
   v testovacím kole „Správně“ / „Správně bylo: 4 7“.
6. Předčasný start (`jump_start`) uprostřed sady: *návrh:* sada pokračuje normálně dalším startem.

**Krok 7 (plán sezení)**
7. Rozdělení 48 startů podmínky do dvou bloků: 9 go a 3 no-go na prodlevu nejdou rozdělit
   napůl. *Návrh:* v každém bloku má každá prodleva přesně 6 startů; dvě prodlevy mají v bloku
   2 no-go a dvě 1 no-go (druhý blok téže podmínky obráceně, které prodlevy losuje seed).
   Každý blok má tak 24 startů a přesně 6 no-go (25 %).
8. „Nejvýš 2 no-go za sebou“: *návrh:* platí v rámci bloku, přes hranice sad ano
   (bloky odděluje pauza).
9. Seed: *návrh:* náhodné celé číslo vygenerované při startu programu, uložené do meta.

**Krok 8 (testovací kolo)**
10. `load` a čísla v testovacím kole: *návrh:* část 1 `load = "none"`, část 2 `load = "low"`,
    obě `block = 0`, `phase = "practice"`. `trial_index` čísluje všechny řádky CSV od 1
    včetně testovacího kola, opakované testovací kolo se zapíše znovu (analýza ho vyřadí podle
    `phase`).

**Krok 9 (instrukce a průběh)**
11. Oslovení účastníka: *návrh:* vykání.
12. Paasova škála: *návrh:* otázka „Kolik duševního úsilí vás stál poslední blok?“, odpověď
    klávesou 1–9 (horní řada i numerická klávesnice), popisky 1 = „velmi, velmi nízké úsilí“,
    5 = „ani nízké, ani vysoké“, 9 = „velmi, velmi vysoké úsilí“.
13. Pauza mezi bloky: *návrh:* bez pevné délky, pokračuje se mezerníkem, text „Pauza.
    Až budete připraveni, stiskněte mezerník.“
14. Texty instrukcí: *návrh:* sepíšu je do tohoto dokumentu ke schválení před krokem 9.

**K zamyšlení (bez nutnosti rozhodnout)**
- 3 no-go na prodlevu a podmínku dávají 12 no-go na podmínku a účastníka. Na H1 celkově to stačí
  (smíšený logistický model přes 30 lidí), na H1 rozdělenou po prodlevách a na H4 je to málo
  dat. Parametry neměním, jen upozorňuji pro interpretaci.

## Kritéria vyřazení (pro analýzu, ne pro program)

- Účastník: přesnost vybavení ve vysoké zátěži pod 50 %, `commission` nad 70 %, nebo víc než
  20 % `omission`.
- Hlavní analýza na všech pokusech, kontrolní jen na sadách se správně vybavenými číslicemi.

## Podmínky měření

- macOS: pevných 60 Hz místo ProMotion; vypnout True Tone, Night Shift, automatický jas;
  režim Nerušit; na nabíječce; spouštět z Terminálu; VS Code během měření zavřený.
- Windows: pevná obnovovací frekvence; ověřit škálování displeje; vypnout oznámení;
  napájení na vysoký výkon.
- Tichá místnost, stejné osvětlení, vzdálenost asi 60 cm, vždy mezerník.

## Parametry (rozhodnuto 12. 11. 2026, neměnit bez dohody)

| parametr | hodnota |
|---|---|
| `LIGHT_INTERVAL` | 1,0 s (jako ve F1) |
| `FOREPERIODS` | 0.5 / 1.25 / 2.0 / 2.75 s |
| `RESPONSE_WINDOW` | 1,5 s |
| `REST_INTERVAL` | 1,0 s, během něj zpětná vazba |
| `ANTICIPATION_THRESHOLD` | 0,1 s |
| vlajka | 500 × 300 px, střed (0, 180); lampy poloměr 40 px na y = −90, rozestup 120 px |
| zpětná vazba | reakční čas v ms a hlášky o chybách, stejná ve všech podmínkách |
| testovací kolo | 4 starty bez číslic + 1 sada s 2 číslicemi |
| hodnocení námahy | Paasova škála 1–9 po každém bloku |

Odhad délky: ostrá část (32 sad) asi 15 minut, celé sezení s instrukcemi a testovacím kolem
asi 20 minut. Při jakékoli změně časů odhad přepočítej.
