"""Konstanty a parametry experimentu (bez PsychoPy)."""

# Okno: "fullscr" (režim celé obrazovky) nebo "borderless" (okno bez okrajů velikosti displeje)
WINDOW_MODES = ("fullscr", "borderless")
WINDOW_MODE = "fullscr"

# Obnovovací frekvence displeje (v Hz), jiná naměřená hodnota ukončí program
EXPECTED_FRAME_RATE = 60
FRAME_RATE_TOLERANCE = 1.0

# Barvy
OFF = "#333333"
ON = "red"
FLAG_COLOR = "#EF9F27"

# Rozložení obrazovky v centimetrech, střed obrazovky je (0, 0). Na pixely se převádí podle
# kalibrace počítače, takže podněty mají na každém displeji stejnou fyzickou velikost
# (krok 2k, 16. 11. 2026). Hodnoty = dřívější pixely na MacBooku Pro 14": na Retině je pixel
# PsychoPy bod displeje (2 × 2 fyzické pixely), tedy 50 px/cm (254 ppi / 2).
N_LAMPS = 5
LAMP_RADIUS = 0.8
LAMP_SPACING = 2.4
LAMP_Y = -1.8
FLAG_WIDTH = 10.0
FLAG_HEIGHT = 6.0
FLAG_POS = (0, 3.6)

# Kalibrace velikosti (docs/experiment.md, „Kalibrace velikosti“): experimentátor šipkami
# srovná šířku obdélníku s kartou formátu ID-1 (platební karta, průkaz), 85,60 × 53,98 mm.
CARD_WIDTH_CM = 8.56
CARD_HEIGHT_CM = 5.398
CARD_COLOR = "#555555"
MM_PER_CM = 10
CALIBRATION_KEYS = {"left": -1, "right": 1, "down": -10, "up": 10}  # změna šířky v px
# Věrohodný rozsah kalibrace: monitor 24" Full HD asi 36, MacBook Pro 14" 50
PX_PER_CM_MIN = 20.0
PX_PER_CM_MAX = 200.0
PX_PER_CM_DECIMALS = 3
# Před první kalibrací: odhad výšky displeje notebooku (MacBook Pro 14" 19,6 cm, 15,6" 16:9
# asi 19,4 cm). Určí velikost písma na kalibrační obrazovce a výchozí šířku obdélníku.
ASSUMED_SCREEN_HEIGHT_CM = 19.6
CALIBRATION_TEXT_Y = 6.0  # cm, návod nad obdélníkem
CALIBRATION_VALUE_Y = -4.5  # cm, naměřená hodnota pod obdélníkem
SIZE_CHECK_TEXT_Y = -4.5  # cm, text pod lampami na obrazovce kontroly velikosti
# PsychoPy na Retině: 1 pix = 2 × 2 fyzické pixely, win.size ale hlásí fyzické pixely
# (retinaScale v psychopy/visual/window.py; ověřeno 16. 11. 2026 obdélníkem 100 pix = 200 px)
RETINA_PIX_SCALE = 2
# Windows: proces „per-monitor DPI aware“ (PROCESS_PER_MONITOR_DPI_AWARE), okno v nativních
# pixelech bez roztažení podle měřítka zobrazení (125 % apod.)
WINDOWS_DPI_AWARENESS = 2

# Časy (v sekundách)
FOREPERIODS = [0.5, 1.25, 2.0, 2.75]
LIGHT_INTERVAL = 1.0
RESPONSE_WINDOW = 1.5
REST_INTERVAL = 1.0
ANTICIPATION_THRESHOLD = 0.1
DIGITS_DURATION = 4.0  # zobrazení číslic na začátku sady (stejně pro 2 i 6 číslic)
DIGITS_BLANK = 0.5  # prázdná obrazovka po číslicích

# Výsledky startu (docs/experiment.md, „Výsledky startu“); jump_start může nastat u obou typů
GO_OUTCOMES = ("jump_start", "anticipation", "go", "omission")
NOGO_OUTCOMES = ("jump_start", "commission", "inhibit")
OUTCOMES_WITH_RT = ("anticipation", "go", "commission")

# Design (docs/experiment.md, „Design“): zátěž a počet ostrých bloků (block 0 = testovací kolo)
LOADS = ("none", "low", "high")
N_BLOCKS = 4

# Paměťová sada (docs/experiment.md, „Průběh jedné sady“, „Číslice a vybavení“)
STARTS_PER_SET = 3
DIGITS_PER_LOAD = {"none": 0, "low": 2, "high": 6}
DIGITS = "0123456789"
DIGITS_HEIGHT = 1.6  # cm
# Česká klávesnice: horní řada bez Shiftu píše tyto znaky; při vybavení se berou jako číslice
# (i velká písmena při Caps Lock). „+“ je i plus na numerické klávesnici (iohub obojí hlásí
# jako num_add), překlep tam zapíše 1; účastník ho vidí a může smazat.
CZECH_DIGIT_ROW = dict(zip("+ěščřžýáíé", "1234567890", strict=True))

# Plán startů
# Testovací kolo (docs/experiment.md, „Testovací kolo“): blok 0, phase "practice".
# Část 1: každá prodleva jednou bez číslic (zapisuje se po startu, set_index 1–4),
# část 2: jedna sada s nízkou zátěží (set_index 5).
PRACTICE_BLOCK = 0
PRACTICE_SINGLE_NOGO = 1  # no-go startů v části 1
PRACTICE_SET_NOGO = 1  # no-go startů v sadě části 2 (návrh, viz docs/experiment.md)
PRACTICE_LOAD = "low"
RECALL_FEEDBACK_DURATION = 2.0  # s, hláška ke správnosti vybavení (jen testovací kolo)
PRACTICE_REPEAT_KEY = "r"
PRACTICE_CONTINUE_KEY = "space"
START_KEY = "space"  # obrazovky „… stiskněte mezerník“ (úvod testovacího kola)
END_KEY = (
    "escape"  # závěrečnou obrazovku zavře jen experimentátor (rozhodnuto 15. 11. 2026)
)
INSTRUCTION_SCREENS = (
    "instructions_1",
    "instructions_2",
    "instructions_3",
    "instructions_4",
)
EFFORT_DIGITS = "123456789"  # Paasova škála 1–9

# Na podmínku a prodlevu (docs/experiment.md, „Plán startů“); podmínka = 2 bloky
GO_PER_FOREPERIOD = 9
NOGO_PER_FOREPERIOD = 3
MAX_NOGO_RUN = 2  # nejvýš tolik no-go startů za sebou v bloku
MAX_SHUFFLES = 10_000  # pojistka: pravidlo splní asi 80 % zamíchání, víc pokusů = chyba
BLOCK_LOADS = {"A": "low", "B": "high"}  # písmena v pořadí bloků ABBA / BAAB
SEED_MAX = 2**31  # seed sezení je náhodné celé číslo 0 … SEED_MAX - 1
# Zkrácený plán pro testy (uv run main.py --short): z každého bloku jen první sady
SHORT_FLAG = "--short"
# Pevný seed jen pro simulaci (--seed=N): stejné sezení pro porovnání před/po úpravě kódu
SEED_FLAG = "--seed"
SHORT_SETS_PER_BLOCK = 1

# Klávesnice (stejný backend na macOS i Windows, viz CLAUDE.md)
KEYBOARD_BACKEND = "iohub"

# Kolik varování o vypadlých snímcích PsychoPy zapíše do logu (výchozích 5 je na sezení málo)
DROPPED_FRAME_WARNINGS_MAX = 100_000

# Data
DATA_DIR_NAME = "data"
# Údaje o počítači v data/: anonymní náhodný identifikátor a kalibrace velikosti. Zapisuje se
# spolu se založením sezení (po obrazovce nastavení), simulace ho nečte ani nemění.
MACHINE_FILE_NAME = "machine.json"
MACHINE_ID_BYTES = 4  # identifikátor = 8 šestnáctkových znaků
MACHINE_ID_CHARS = "0123456789abcdef"  # jak je píše secrets.token_hex
META_SUFFIX = "_meta.json"
LOG_SUFFIX = "_log.txt"
PILOT_PREFIX = "pilot"  # nick pilot… → data/pilot/, mimo střídání pořadí bloků
TEST_PREFIX = "test"  # nick test… → data/test/ (vývoj), mimo střídání pořadí bloků

# Úvodní obrazovky (pro experimentátora, česky)
NICK_CHARS = "abcdefghijklmnopqrstuvwxyz0123456789_-"
NICK_MIN_LENGTH = 2
NICK_MAX_LENGTH = 16
ENTER_KEYS = ("return", "num_enter")
BACKSPACE_KEY = "backspace"
BLOCK_ORDERS = ("ABBA", "BAAB")  # A = nízká zátěž, B = vysoká; sudý počet sezení → ABBA
BLOCK_ORDER_KEYS = {"a": "ABBA", "b": "BAAB"}
LANGUAGE_KEYS = {"c": "cs", "e": "en"}
LANGUAGES = ("cs", "en")
DEFAULT_LANGUAGE = "cs"
LANGUAGE_NAMES = {"cs": "čeština", "en": "English"}
# Texty: výška písma a pozice řádků v cm (převod na pixely podle kalibrace)
TEXT_HEIGHT = 0.8
# Zpětná vazba v pauze: nad lampami (lampy sahají do y = -1,0, vlajka v pauze není)
FEEDBACK_Y = 1.2
FEEDBACK_HEIGHT = 1.2
PROMPT_Y = 2.4  # pozice řádků na obrazovce s nickem a s vybavením
INPUT_Y = 0.0
MESSAGE_Y = -2.4
CURSOR = "_"
# Podíl viditelné šířky okna, na který se text zalomí. Nejdelší schválený řádek má na Macu
# 91 % šířky, takže se nezalomí; delší řádek (nastavení s dlouhým nickem) nepřeteče přes okraj.
TEXT_WRAP_SHARE = 0.95
TEXT_COLOR = "white"
WARNING_COLOR = "#EF9F27"
NICK_PROMPT = (
    "Nick účastníka (malá písmena a–z, číslice, - a _, 2–16 znaků), Enter = potvrdit"
)
NICK_INVALID = "Neplatný nick: 2–16 znaků, jen malá písmena a–z, číslice, - a _."
NICK_EXISTS = "Nick {nick} už existuje. Enter = přesto pokračovat, Backspace = opravit"
ORDER_AUTO = "automaticky podle {completed} dokončených sezení na tomto počítači"
ORDER_MANUAL = "přepsáno ručně, automaticky by bylo {auto_order}"
FOLDER_NOTE = {
    "": "data/",
    "pilot": "data/pilot/ (pilot, nepočítá se)",
    "test": "data/test/ (test, nepočítá se)",
    "sim": "data/sim/ (simulace)",
}
SETTINGS_SCREEN = (
    "Účastník: {nick}    data: {folder}\n\n"
    "Pořadí bloků: {block_order}    ({order_note})\n"
    "A = ABBA, B = BAAB\n\n"
    "Jazyk účastníka: {language_name}\n"
    "C = čeština, E = English\n\n"
    "Počítač: {machine} ({machine_id})\n"
    "Velikost podnětů: {calibration}\n"
    "K = kalibrovat znovu, V = ověřit pravítkem\n\n"
    "Enter = začít sezení"
)
# Klávesy obrazovky nastavení, které otevřou jinou obrazovku (pak se nastavení vrátí)
SETTINGS_START = "start"
SETTINGS_CALIBRATE = "calibrate"
SETTINGS_CHECK_SIZE = "check_size"
SETTINGS_ACTIONS = {"k": SETTINGS_CALIBRATE, "v": SETTINGS_CHECK_SIZE}
CALIBRATION_NOTE = "{px_per_cm} px/cm, kalibrace {date}"
CALIBRATION_NOTE_SIM = "{px_per_cm} px/cm (simulace, bez kalibrace)"
CALIBRATION_SCREEN = (
    "Kalibrace velikosti obrazovky\n\n"
    "Přiložte na obrazovku platební kartu ({card_width} × {card_height} mm) a šipkami upravte\n"
    "šedý obdélník na stejnou šířku jako karta.\n"
    "Šipky vlevo / vpravo = o 1 px, nahoru / dolů = o 10 px, Enter = uložit"
)
CALIBRATION_VALUE = "Šířka obdélníku {width} px = {px_per_cm} px/cm"
CALIBRATION_ADJUST_FIRST = "Enter uloží až po úpravě šipkami (i když už obdélník sedí)."
CALIBRATION_INVALID = (
    "Mimo věrohodný rozsah {minimum}–{maximum} px/cm, upravte šířku obdélníku."
)
SIZE_CHECK_SCREEN = (
    "Ověření velikosti pravítkem\n"
    "Vlajka: {flag_width} × {flag_height} cm, průměr světla {lamp_diameter} cm, "
    "středy světel po {lamp_spacing} cm\n\n"
    "Enter = zpět"
)

# Texty pro účastníka v obou jazycích (docs/experiment.md, „Texty pro účastníka“)
TEXTS = {
    "cs": {
        "feedback_go": "Reakce {rt_ms} ms",
        "feedback_false_start": "Předčasný start!",
        "feedback_commission": "Start pod žlutou vlajkou!",
        "feedback_inhibit": "Správně, bez startu",
        "feedback_omission": "Bez reakce",
        "recall_prompt": "Napište číslice a stiskněte Enter.",
        "recall_correct": "Správně",
        "recall_wrong": "Správně bylo: {digits}",
        "effort_question": "Kolik duševního úsilí vás stál poslední blok?",
        "effort_low": "1 = velmi, velmi nízké úsilí",
        "effort_mid": "5 = ani nízké, ani vysoké",
        "effort_high": "9 = velmi, velmi vysoké úsilí",
        "block_pause": (
            "Pauza.\n\n"
            "Další bude blok {next_block} ze {n_blocks}.\n"
            "Až budete připraveni, stiskněte mezerník."
        ),
        "instructions_1": (
            "Vítejte a děkujeme za účast.\n\n"
            "Budete startovat jako jezdec formule 1 a zároveň si pamatovat číslice.\n"
            "Celé sezení trvá asi 20 minut.\n\n"
            "Mezerník = dál"
        ),
        "instructions_2": (
            "Na obrazovce je semafor s pěti světly. Světla se postupně rozsvítí\n"
            "a po chvíli všechna najednou zhasnou.\n\n"
            "Jakmile zhasnou, co nejrychleji stiskněte mezerník.\n"
            "Nestiskněte ho dřív, to je předčasný start.\n\n"
            "Mezerník = dál"
        ),
        "instructions_3": (
            "Někdy se ve chvíli zhasnutí objeví žlutá vlajka.\n"
            "Pak mezerník nemačkejte.\n\n"
            "Mezerník = dál"
        ),
        "instructions_4": (
            "Před každými třemi starty se na chvíli ukážou číslice. Zapamatujte si je.\n"
            "Po třech startech je napište ve stejném pořadí a potvrďte Enterem.\n\n"
            "Obě úlohy jsou stejně důležité: reagujte rychle a přesně\n"
            "a zároveň si číslice zapamatujte.\n\n"
            "Mezerník = dál"
        ),
        "practice_set_intro": (
            "Teď si vyzkoušíte sadu s číslicemi.\n\nMezerník = začít"
        ),
        "main_start": (
            "Teď začíná měření.\n\n"
            "Má {n_blocks} bloky, mezi nimi si můžete odpočinout.\n"
            "Zpětnou vazbu k číslicím už neuvidíte.\n\n"
            "Mezerník = začít"
        ),
        "effort_hint": "Stiskněte číslo 1–9 (jde změnit), pak Enter.",
        "effort_selected": "Vybráno: {rating}",
        "end": (
            "Měření je hotové, děkujeme!\n\n"
            "Vaše výsledky:\n"
            "Průměrná reakce: {mean_rt} ms\n"
            "Předčasné starty: {false_starts} z {starts}\n"
            "Starty pod žlutou vlajkou: {commissions} z {nogo}\n"
            "Správně zapamatované číslice:\n"
            "2 číslice {recall_low} %, 6 číslic {recall_high} %\n\n"
            "Zavolejte prosím experimentátora."
        ),
        "practice_start": (
            "Testovací kolo\n\n"
            "Vyzkoušíte si několik startů a jednu sadu s číslicemi.\n"
            "Výsledky testovacího kola se nezapočítávají.\n\n"
            "Mezerník = začít"
        ),
        "practice_end": (
            "Konec testovacího kola.\n\n"
            "R = zopakovat testovací kolo\nMezerník = pokračovat do měření"
        ),
    },
    "en": {
        "feedback_go": "Reaction {rt_ms} ms",
        "feedback_false_start": "False start!",
        "feedback_commission": "Started under the yellow flag!",
        "feedback_inhibit": "Correct, no start",
        "feedback_omission": "No reaction",
        "recall_prompt": "Type the digits and press Enter.",
        "recall_correct": "Correct",
        "recall_wrong": "The correct answer was: {digits}",
        "effort_question": "How much mental effort did the last block take?",
        "effort_low": "1 = very, very low mental effort",
        "effort_mid": "5 = neither low nor high mental effort",
        "effort_high": "9 = very, very high mental effort",
        "block_pause": (
            "Break.\n\n"
            "Next is block {next_block} of {n_blocks}.\n"
            "When you are ready, press the space bar."
        ),
        "instructions_1": (
            "Welcome and thank you for taking part.\n\n"
            "You will start like a Formula 1 driver and remember digits at the same time.\n"
            "The whole session takes about 20 minutes.\n\n"
            "Space = next"
        ),
        "instructions_2": (
            "The screen shows a start light with five lamps. The lamps light up one by one\n"
            "and after a moment all go out at once.\n\n"
            "As soon as they go out, press the space bar as fast as you can.\n"
            "Do not press it earlier, that is a false start.\n\n"
            "Space = next"
        ),
        "instructions_3": (
            "Sometimes a yellow flag appears at the moment the lamps go out.\n"
            "Then do not press the space bar.\n\n"
            "Space = next"
        ),
        "instructions_4": (
            "Before every three starts, digits appear for a moment. Remember them.\n"
            "After the three starts, type them in the same order and press Enter.\n\n"
            "Both tasks are equally important: react quickly and accurately\n"
            "and remember the digits.\n\n"
            "Space = next"
        ),
        "practice_set_intro": ("Now you will try a set with digits.\n\nSpace = start"),
        "main_start": (
            "The experiment starts now.\n\n"
            "It has {n_blocks} blocks, you can rest between them.\n"
            "You will no longer see feedback on the digits.\n\n"
            "Space = start"
        ),
        "effort_hint": "Press a number 1–9 (you can change it), then Enter.",
        "effort_selected": "Selected: {rating}",
        "end": (
            "The session is finished, thank you!\n\n"
            "Your results:\n"
            "Average reaction: {mean_rt} ms\n"
            "False starts: {false_starts} of {starts}\n"
            "Starts under the yellow flag: {commissions} of {nogo}\n"
            "Digits remembered correctly:\n"
            "2 digits {recall_low} %, 6 digits {recall_high} %\n\n"
            "Please call the experimenter."
        ),
        "practice_start": (
            "Practice round\n\n"
            "You will try a few starts and one set with digits.\n"
            "The practice round does not count.\n\n"
            "Space = start"
        ),
        "practice_end": (
            "End of the practice round.\n\n"
            "R = repeat the practice round\nSpace = continue to the experiment"
        ),
    },
}
MACHINE_CODES = {"darwin": "mac", "win32": "win"}
CSV_COLUMNS = (
    "participant",
    "machine",
    "phase",
    "block",
    "load",
    "set_index",
    "start_in_set",
    "trial_index",
    "foreperiod_s",
    "is_nogo",
    "outcome",
    "rt_ms",
    "digits_shown",
    "digits_typed",
    "recall_correct",
    "dropped_frames",
    "timestamp",
)

# Simulace (uv run main.py --sim): falešná klávesnice podle scénáře, bez člověka
SIM_FLAG = "--sim"
SIM_ESCAPE_FLAG = (
    "--sim-escape"  # simulace, která Escapem přeruší start č. SIM_ESCAPE_AT
)
# Pořadí startu od začátku sezení (2 testovací kola po 7 startech, pak ostrá část):
# 19 = prostřední start 2. ostré sady, rozdělaná sada se nesmí zapsat.
SIM_ESCAPE_AT = 19
SIM_PRACTICE_ROUNDS = 2  # simulace testovací kolo jednou zopakuje (R), pak mezerník
SIM_EFFORT_RATINGS = ("3", "6", "4", "8")  # hodnocení bloků 1–4 na Paasově škále
SIM_NICK = "sim"
SIM_LANGUAGE = "en"
# Klávesy, které simulace „napíše“ na úvodních obrazovkách: příliš krátký nick (chyba),
# Backspace, nick „sim“; na nastavení kalibrace (K, šipky tam a zpět, Enter: zůstane
# SIM_PX_PER_CM), ověření velikosti (V, Enter), přepnutí jazyka na EN, start sezení.
SIM_CALIBRATION_KEYS = ("k", "right", "up", "left", "down", "return")
SIM_INTRO_KEYS = (
    *("x", "return", "backspace", "s", "i", "m", "return"),
    *SIM_CALIBRATION_KEYS,
    *("v", "return", "e", "return"),
)
# Simulace uloží obrázek první pauzy po každém typu výsledku (obsah okna PsychoPy,
# ne obrazovky). Okno simulace je na Retině v pix malé (pix = bod displeje), obrázek proto
# ukáže jen střed (vlajka se nevejde) a text se zalomí víc než na celé obrazovce;
# vzhled ověřuje ruční test.
SIM_SCREENS_SUFFIX = "_screens"
# Vybavení číslic v simulaci se střídá: správně, špatná poslední číslice, překlep opravený
# Backspacem, kratší odpověď (jen první číslice).
SIM_RECALL_CYCLE = ("correct", "wrong", "corrected", "short")
SIM_DIR_NAME = "sim"
# Simulace nekalibruje: pevná velikost (jako MacBook Pro 14") a pevný identifikátor počítače.
SIM_PX_PER_CM = 50.0
SIM_MACHINE_ID = "00000000"
# Simulace běží v menším okně uprostřed (jen pro ni, ostrý běh ho nedostane), aby nechala
# volnou obrazovku. Okno je aspoň tak velké, aby se vešly lampy i vlajka s okrajem.
SIM_WINDOW_MODE = "windowed"
SIM_WINDOW_SCALE = 0.4  # podíl velikosti displeje
SIM_WINDOW_MARGIN = 40  # px kolem podnětů (okno simulace je v pixelech)
SIM_KEYBOARD_BACKEND = "simulated"
# Typy odpovědí: čas stisku vůči zhasnutí v sekundách (záporný = těsně před zhasnutím,
# přečtený až v prvním snímku okna odpovědi); "early" = stisk během rozsvěcování lamp,
# "none" = bez stisku, "escape" = Escape na začátku startu (přerušení sezení).
SIM_PRESS_RT = {"late_early": -0.02, "fast": 0.05, "normal": 0.25}
SIM_EARLY_PRESS = 2.0  # s od začátku startu, lampy svítí 4 × LIGHT_INTERVAL
# Odpovědi se pro go a no-go starty střídají dokola, aby padlo všech 6 výsledků.
SIM_GO_CYCLE = ("normal", "fast", "none", "early")
SIM_NOGO_CYCLE = ("none", "normal", "late_early", "fast")

# Hláška zpětné vazby podle výsledku startu (klíč v TEXTS, docs/experiment.md)
FEEDBACK_KEYS = {
    "go": "feedback_go",
    "jump_start": "feedback_false_start",
    "anticipation": "feedback_false_start",
    "commission": "feedback_commission",
    "inhibit": "feedback_inhibit",
    "omission": "feedback_omission",
}
