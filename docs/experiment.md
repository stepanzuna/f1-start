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

1. Zobrazení číslic na 4 s (`DIGITS_DURATION`, stejně pro 2 i 6 číslic), pak 0,5 s prázdná
   obrazovka. Změněno z 2 s 13. 11. 2026 po ručním testu: 6 číslic za 2 s nešlo zapamatovat.
   Stejný čas pro obě zátěže, aby se podmínky lišily jen počtem číslic.
2. Třikrát start:
   - lampy 1–4 se rozsvěcují po 1,0 s (`LIGHT_INTERVAL`),
   - pak se rozsvítí lampa 5 a svítí **přesně po dobu prodlevy** (`FOREPERIODS` = 0.5 / 1.25 / 2.0 / 2.75 s),
   - zhasnutí; u no-go startu se **ve stejném snímku** objeví žlutá vlajka (obdélník nad lampami),
   - okno odpovědi 1,5 s (`RESPONSE_WINDOW`), odpověď mezerníkem,
   - pauza 1,0 s (`REST_INTERVAL`), během ní zpětná vazba.
3. Vybavení: účastník napíše číslice a potvrdí Enterem.

Předčasný start (`jump_start`) uprostřed sady sadu nepřerušuje, pokračuje se dalším startem.

Po každém bloku: hodnocení vnímané námahy na Paasově škále 1–9 a pauza (viz Texty pro účastníka).

## Číslice a vybavení (rozhodnuto 13. 11. 2026)

- Generování: náhodně 0–9 **bez opakování** v rámci sady, nula smí být první. Číslice se
  generují předem v plánu sezení, stejný seed = stejné číslice.
- Zobrazení: všechny číslice najednou uprostřed obrazovky, oddělené mezerou („4 7 1 9 0 3“),
  bílé písmo, výška 80 px.
- Vybavení: bez časového limitu. Přijímá jen číslice 0–9, nejvýš tolik, kolik jich bylo
  zobrazeno, Backspace maže. Enter potvrdí i kratší odpověď.
- `recall_correct = True` jen při přesné shodě celé sekvence včetně pořadí.
- Psaní číslic (krok 6): horní řada, numerická klávesnice i česká horní řada bez Shiftu
  („+ěščřžýáíé“ = 1234567890). Na obrazovce vybavení je výzva ve zvoleném jazyce a napsané
  číslice velikostí 80 px, oddělené mezerou.
- Číslice jsou v plánu v samostatném slovníku podle (blok, pořadí sady); `Start` se nemění.
- Zpětná vazba k vybavení: v ostré části žádná (stejné ve všech podmínkách), v testovacím kole
  „Správně“ nebo „Správně bylo: 4 7“.

## Plán startů

- Na každou podmínku: každá prodleva 9× go a 3× no-go (25 % no-go). Plán se vygeneruje
  systematicky smyčkami a pak zamíchá.
- Nejvýš 2 no-go starty za sebou: zamíchat, zkontrolovat, případně míchat znovu. Pravidlo platí
  v rámci bloku, přes hranice sad ano (bloky odděluje pauza).
- Plán podmínky (48 startů) se rozdělí do jejích dvou bloků po 24 startech (rozhodnuto
  13. 11. 2026): v každém bloku má každá prodleva přesně 6 startů. Dvě prodlevy mají v bloku
  2 no-go a 4 go, dvě 1 no-go a 5 go, druhý blok téže podmínky obráceně. Které prodlevy dostanou
  2 no-go, losuje seed. Každý blok má tak 24 startů a přesně 6 no-go (25 %). Zamíchaný blok
  se rozdělí na 8 sad po 3 startech.
- Náhoda přes `random.Random(seed)`. Seed je náhodné celé číslo vygenerované při spuštění
  programu a ukládá se do metadat.
- Implementace (krok 7, 13. 11. 2026): `build_session(pořadí bloků, seed, short)` v `logic.py`
  vytvoří plán i číslice; stejný seed a pořadí dají přesně stejné sezení. `check_data.py`
  plán ze seedu v meta přegeneruje a porovná s CSV.
- Zkrácený plán pro testy (`uv run main.py --short`, i se `--sim`): z každého bloku jen
  první sada, tedy 12 startů ve 4 blocích. V meta `short = true`. Program ho povolí jen
  v simulaci a s nickem `test…` (jinak skončí hned po zadání nicku, nic nezapíše),
  do střídání pořadí bloků se nepočítá a `check_data.py` ho u ostrého sezení hlásí.

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

| výsledek | česky | anglicky |
|---|---|---|
| `go` | „Reakce 213 ms“ | “Reaction 213 ms” |
| `jump_start`, `anticipation` | „Předčasný start!“ | “False start!” |
| `commission` | „Start pod žlutou vlajkou!“ | “Started under the yellow flag!” |
| `inhibit` | „Správně, bez startu“ | “Correct, no start” |
| `omission` | „Bez reakce“ | “No reaction” |

Hláška se zobrazí ve zvoleném jazyce po celou pauzu (`REST_INTERVAL`) nad zhasnutými lampami:
střed na y = 60 px, výška písma 60 px, bílá (krok 5, 13. 11. 2026; lampy sahají do y = −50,
mezera asi 80 px). Text se nastaví jednou před pauzou, mimo měřený start.

## Úvodní obrazovka a nick

- Dvě obrazovky pro experimentátora (česky, krok 4):
  1. **Nick:** experimentátor napíše nick a potvrdí Enterem.
  2. **Nastavení:** ukáže nick, počítač, přiřazené pořadí bloků a jazyk účastníka.
     `A` = ABBA, `B` = BAAB, `C` = čeština, `E` = English, Enter = začít sezení.
     Volby jsou na zvláštní obrazovce, protože písmena A/B/C/E se dají psát i do nicku.
- Textový vstup čte znaky z `KeyPress.code` (napsaný znak včetně Shiftu a rozložení
  klávesnice), ovládací klávesy z `KeyPress.name` (`return`, `num_enter`, `backspace`,
  `escape`; ověřeno ve zdrojácích iohub pro macOS i Windows). Česká horní řada bez Shiftu
  („ěščř…“) se do nicku nepíše, číslice jdou se Shiftem nebo z numerické klávesnice.
- Nick: malá písmena a–z, číslice, `-` a `_`, délka 2–16 znaků. Nesmí to být skutečné jméno.
- Pokud v `data/` už existuje soubor se stejným nickem: hláška „Nick už existuje.
  Enter = přesto pokračovat, Backspace = opravit“. Nový soubor má jiný čas v názvu,
  nic se nepřepíše.
- Pořadí bloků: program spočítá dokončená ostrá sezení v `data/` na tomto počítači
  (meta s `aborted = False`, bez pilotu, testů a simulace). Sudý počet → ABBA, lichý → BAAB.
  Obrazovka nastavení přiřazené pořadí ukáže a experimentátor ho může klávesou A/B přepsat.
- Jazyk účastníka (rozhodnuto 13. 11. 2026): čeština nebo angličtina, volí experimentátor
  na obrazovce nastavení (výchozí čeština). Celé sezení běží v jednom jazyce, ukládá se do meta
  (`language` = `cs` / `en`) a v analýze může být faktor. Dva jazyky naráz se nezobrazují,
  aby zpětná vazba (čtená během 1 s pauzy pod paměťovou zátěží) zůstala krátká.
- Pilotní sezení: nick začínající `pilot` se ukládá do `data/pilot/` a do střídání se nepočítá.
- Testovací běhy při vývoji: nick začínající `test` se ukládá do `data/test/` a do střídání
  se nepočítá (rozhodnuto 13. 11. 2026). Starší soubory `data/test_*` z kroku 3 před sběrem dat
  smazat nebo přesunout do `data/test/`.

## Testovací kolo

- Po zadání nicku a instrukcích, před ostrou částí.
- Část 1: 4 starty bez číslic, každý s jinou prodlevou, z toho 1 no-go.
  Část 2: 1 sada (3 starty) s 2 číslicemi.
- Zpětná vazba ke startům stejná jako v ostré části, navíc zpětná vazba k vybavení číslic.
- Na konci: `R` = zopakovat testovací kolo, mezerník = pokračovat do ostré části.
- Ukládá se do stejného CSV: část 1 `load = "none"`, část 2 `load = "low"`, obě `block = 0`
  a `phase = "practice"`. `trial_index` čísluje všechny řádky CSV od 1 včetně testovacího kola.
  Opakované testovací kolo se zapíše znovu, analýza ho vyřadí podle `phase`.
- Implementace (krok 8, 13. 11. 2026):
  - Kolo se tvoří ze seedu sezení vlastním generátorem (`build_practice`), takže plán ostré
    části zůstane stejný. Opakované kolo má jiné prodlevy i číslice, ze stejného seedu ale
    vždy stejné. `check_data.py` testovací kola přegeneruje a porovná s CSV.
  - V CSV: část 1 má `set_index` 1–4 a `start_in_set` 1 (zápis po každém startu),
    sada části 2 má `set_index` 5 a `start_in_set` 1–3.
  - Úvodní obrazovka před každým kolem (přidáno 14. 11. 2026 na žádost autora, ve zvoleném
    jazyce): „Testovací kolo. Vyzkoušíte si několik startů a jednu sadu s číslicemi. Výsledky
    testovacího kola se nezapočítávají. Mezerník = začít“ (EN: “Practice round. You will try
    a few starts and one set with digits. The practice round does not count. Space = start”).
  - Obrazovka po kole (ve zvoleném jazyce): „Konec testovacího kola. R = zopakovat testovací
    kolo, Mezerník = pokračovat do měření“ (EN: “End of the practice round. R = repeat the
    practice round, Space = continue to the experiment”).
  - Návrhy čekající na schválení: viz Otevřené otázky 1–2.

## Texty pro účastníka (rozhodnuto 13. 11. 2026)

Všechny texty pro účastníka jsou česky i anglicky v `TEXTS` v `config.py` (test hlídá, že oba
jazyky mají stejné texty). Anglické znění doplněno 13. 11. 2026, překlad ke kontrole.

- Oslovení: vykání (EN: neutrální „you“).
- Paasova škála po každém bloku: otázka „Kolik duševního úsilí vás stál poslední blok?“
  (“How much mental effort did the last block take?”), odpověď klávesou 1–9 (horní řada
  i numerická klávesnice). Popisky: 1 = „velmi, velmi nízké úsilí“ (“very, very low mental
  effort”), 5 = „ani nízké, ani vysoké“ (“neither low nor high mental effort”),
  9 = „velmi, velmi vysoké úsilí“ (“very, very high mental effort”).
- Pauza mezi bloky: bez pevné délky, text „Pauza. Až budete připraveni, stiskněte mezerník.“
  Rozšířeno o „Další bude blok X ze 4“ (schváleno 15. 11. 2026).
- Rozhodnuto 15. 11. 2026 (krok 9):
  - Paasova škála: číslo 1–9 se nejdřív jen vybere („Vybráno: 7“), jde změnit jiným číslem
    a uloží se až Enterem, aby se neuložila číslice stisknutá omylem hned po vybavení.
  - Závěrečnou obrazovku se zhodnocením zavře jen Escape (experimentátor). Data jsou v tu
    chvíli už uložená.
  - Práh anticipace (0,1 s) se v instrukcích nevysvětluje (autor nerozhodl, ponechán návrh):
    znalost prahu by mohla změnit strategii účastníků; hláška „Předčasný start!“ stačí.
  (“Break. When you are ready, press the space bar.”)
- Vybavení číslic: „Napište číslice a stiskněte Enter.“ (“Type the digits and press Enter.”),
  v testovacím kole „Správně“ / „Správně bylo: 4 7“ (“Correct” / “The correct answer was: 4 7”).
- Texty instrukcí a dalších obrazovek: viz „Texty obrazovek (krok 9)“ níže.

### Texty obrazovek (krok 9, schváleno autorem 15. 11. 2026)

Všechny texty obrazovek pro účastníka v pořadí, jak se v sezení objeví. Vygenerováno
z `TEXTS` v `config.py` (program je zobrazuje přesně takto). Proměnné ve složených
závorkách program doplní. Paasova škála a hlášky zpětné vazby jsou schválené výše.

**Instrukce 1 (úvod)** (`instructions_1`)

Česky:

> Vítejte a děkujeme za účast.
>
> Budete startovat jako jezdec formule 1 a zároveň si pamatovat číslice.
> Celé sezení trvá asi 20 minut.
>
> Mezerník = dál

Anglicky:

> Welcome and thank you for taking part.
>
> You will start like a Formula 1 driver and remember digits at the same time.
> The whole session takes about 20 minutes.
>
> Space = next

**Instrukce 2 (semafor)** (`instructions_2`)

Česky:

> Na obrazovce je semafor s pěti světly. Světla se postupně rozsvítí
> a po chvíli všechna najednou zhasnou.
>
> Jakmile zhasnou, co nejrychleji stiskněte mezerník.
> Nestiskněte ho dřív, to je předčasný start.
>
> Mezerník = dál

Anglicky:

> The screen shows a start light with five lamps. The lamps light up one by one
> and after a moment all go out at once.
>
> As soon as they go out, press the space bar as fast as you can.
> Do not press it earlier, that is a false start.
>
> Space = next

**Instrukce 3 (žlutá vlajka)** (`instructions_3`)

Česky:

> Někdy se ve chvíli zhasnutí objeví žlutá vlajka.
> Pak mezerník nemačkejte.
>
> Mezerník = dál

Anglicky:

> Sometimes a yellow flag appears at the moment the lamps go out.
> Then do not press the space bar.
>
> Space = next

**Instrukce 4 (číslice)** (`instructions_4`)

Česky:

> Před každými třemi starty se na chvíli ukážou číslice. Zapamatujte si je.
> Po třech startech je napište ve stejném pořadí a potvrďte Enterem.
>
> Obě úlohy jsou stejně důležité: reagujte rychle a přesně
> a zároveň si číslice zapamatujte.
>
> Mezerník = dál

Anglicky:

> Before every three starts, digits appear for a moment. Remember them.
> After the three starts, type them in the same order and press Enter.
>
> Both tasks are equally important: react quickly and accurately
> and remember the digits.
>
> Space = next

**Úvod testovacího kola** (`practice_start`)

Česky:

> Testovací kolo
>
> Vyzkoušíte si několik startů a jednu sadu s číslicemi.
> Výsledky testovacího kola se nezapočítávají.
>
> Mezerník = začít

Anglicky:

> Practice round
>
> You will try a few starts and one set with digits.
> The practice round does not count.
>
> Space = start

**Předěl před sadou s číslicemi** (`practice_set_intro`)

Česky:

> Teď si vyzkoušíte sadu s číslicemi.
>
> Mezerník = začít

Anglicky:

> Now you will try a set with digits.
>
> Space = start

**Konec testovacího kola** (`practice_end`)

Česky:

> Konec testovacího kola.
>
> R = zopakovat testovací kolo
> Mezerník = pokračovat do měření

Anglicky:

> End of the practice round.
>
> R = repeat the practice round
> Space = continue to the experiment

**Začátek měření** (`main_start`)

Česky:

> Teď začíná měření.
>
> Má {n_blocks} bloky, mezi nimi si můžete odpočinout.
> Zpětnou vazbu k číslicím už neuvidíte.
>
> Mezerník = začít

Anglicky:

> The experiment starts now.
>
> It has {n_blocks} blocks, you can rest between them.
> You will no longer see feedback on the digits.
>
> Space = start

**Pauza mezi bloky** (`block_pause`)

Česky:

> Pauza.
>
> Další bude blok {next_block} ze {n_blocks}.
> Až budete připraveni, stiskněte mezerník.

Anglicky:

> Break.
>
> Next is block {next_block} of {n_blocks}.
> When you are ready, press the space bar.

**Pokyn pod Paasovou škálou** (`effort_hint`)

Česky:

> Stiskněte číslo 1–9 (jde změnit), pak Enter.
>
> Vybráno: {rating}

Anglicky:

> Press a number 1–9 (you can change it), then Enter.
>
> Selected: {rating}

**Závěr se zhodnocením** (`end`)

Česky:

> Měření je hotové, děkujeme!
>
> Vaše výsledky:
> Průměrná reakce: {mean_rt} ms
> Předčasné starty: {false_starts} z {starts}
> Starty pod žlutou vlajkou: {commissions} z {nogo}
> Správně zapamatované číslice:
> 2 číslice {recall_low} %, 6 číslic {recall_high} %
>
> Zavolejte prosím experimentátora.

Anglicky:

> The session is finished, thank you!
>
> Your results:
> Average reaction: {mean_rt} ms
> False starts: {false_starts} of {starts}
> Starts under the yellow flag: {commissions} of {nogo}
> Digits remembered correctly:
> 2 digits {recall_low} %, 6 digits {recall_high} %
>
> Please call the experimenter.

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
pořadí bloků, jazyk účastníka (`language`), seed, naměřená frekvence, režim okna, backend klávesnice,
kopie všech časových konstant, hodnocení námahy po blocích, vypadlé snímky celkem.
Doplněno 13. 11. 2026: skutečná velikost okna v px, `simulated` (režim simulace),
`planned_starts` (počet startů v plánu sezení), u git commitu přípona `-dirty`, když běžel
kód s necommitnutými změnami. `keyboard_backend` je backend, který PsychoPy skutečně použil;
když to není `iohub`, program skončí ještě před otevřením okna.

Meta se zapíše po obrazovce nastavení (před prvním startem) s `aborted = true` a `ended_at = null`. Na řádném konci
sezení se přepíše (`aborted = false`, konec, vypadlé snímky celkem). Přerušené sezení tak má
vždy `aborted = true`, ať skončilo Escapem, pádem programu, nebo vypnutím počítače.

Log `…_log.txt`: varování PsychoPy během sezení (hlavně vypadlé snímky `t of last frame was …ms`),
pro kontrolu kvality měření.

Simulace (`uv run main.py --sim`) ukládá do `data/sim/`, testovací běhy (nick `test…`)
do `data/test/`, pilot do `data/pilot/`. Nic z toho se nepočítá do střídání pořadí bloků
ani do analýzy.

Simulace (krok 3s, 13. 11. 2026): místo klávesnice „mačká“ program sám podle scénáře, který
se odvodí z plánu tak, aby padly všechny výsledky. Nick `sim`, okno menší (40 % displeje,
aspoň tak velké, aby se vešly podněty; jen pro simulaci), `keyboard_backend = "simulated"`,
v meta navíc `sim_scenario` (typ odpovědi pro každý start). `check_data.py` u simulace porovná
výsledek a reakční čas každého startu s předpovědí scénáře. Simulace projde testovací kolo,
zopakuje ho (`R`) a pokračuje mezerníkem. `--sim-escape` stiskne Escape v 19. startu
(uprostřed 2. ostré sady po dvou testovacích kolech) a ověří přerušené sezení i to,
že se rozdělaná sada nezapíše. Simulace neověřuje vzhled ani časování.

## Otevřené otázky

Otázky z 13. 11. 2026 (první várka) jsou rozhodnuté a zapsané v sekcích výše.
Nové otázky se zapisují sem s návrhem; po rozhodnutí se přesunou do příslušné sekce.

**Krok 8 (testovací kolo)**
1. No-go v sadě s číslicemi v testovacím kole (část 2: číslice → 3 starty → vybavení):
   *návrh (implementováno):* 1 ze 3 startů je no-go (`PRACTICE_SET_NOGO = 1`), aby si účastník
   vyzkoušel vlajku i pod paměťovou zátěží (v ostré části mají sady no-go taky).
   Alternativa: 0 (sada jen s go starty). *Potvrzeno autorem 14. 11. 2026.*

Rozhodnuto 14. 11. 2026 (autor):
- Hláška „Správně“ / „Správně bylo: 4 7“ po vybavení v testovacím kole svítí 2 s
  (`RECALL_FEEDBACK_DURATION`).
- Prodlevy v testovacím kole náhodně (sada části 2 má 3 různé ze 4, no-go na náhodném místě).
  Mezi částí 1 a 2 se ukáže krátký text „Teď si vyzkoušíte sadu s číslicemi“
  (implementuje krok 9 spolu s ostatními texty).
- Texty obrazovek testovacího kola se schválí s ostatními texty v kroku 9.
- V ostré části žádná zpětná vazba k vybavení (potvrzeno).
- Na konci sezení celkové zhodnocení (krok 9): závěrečná obrazovka po poděkování ukáže souhrn
  z ostré části: průměrný reakční čas (go), počet předčasných startů, starty pod vlajkou
  z celkového počtu no-go a podíl správně vybavených sad, zvlášť pro 2 a 6 číslic. Zobrazí se
  až po uložení všech dat, takže měření neovlivní.

## Poznámky k analýze

- 3 no-go na prodlevu a podmínku dávají 12 no-go na podmínku a účastníka. Na H1 celkově to stačí
  (smíšený logistický model přes 30 lidí), na H1 rozdělenou po prodlevách a na H4 je to málo
  dat. Parametry se nemění, jen to vzít v úvahu při interpretaci.

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
| `DIGITS_DURATION` | 4,0 s zobrazení číslic, stejně pro obě zátěže (změněno 13. 11. 2026 z 2 s) |
| `DIGITS_BLANK` | 0,5 s prázdná obrazovka po číslicích |
| hodnocení námahy | Paasova škála 1–9 po každém bloku |

Odhad délky: simulace ostré části s 2 s číslicemi trvala 11:41 min (13. 11. 2026); se 4 s
číslicemi (+64 s) a psaním odpovědí účastníkem asi 15–16 minut, celé sezení s instrukcemi a testovacím kolem
asi 20 minut. Při jakékoli změně časů odhad přepočítej.
