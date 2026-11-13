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

# Rozložení obrazovky (v pixelech, střed obrazovky je (0, 0))
N_LAMPS = 5
LAMP_RADIUS = 40
LAMP_SPACING = 120
LAMP_Y = -90
FLAG_WIDTH = 500
FLAG_HEIGHT = 300
FLAG_POS = (0, 180)

# Časy (v sekundách)
FOREPERIODS = [0.5, 1.25, 2.0, 2.75]
LIGHT_INTERVAL = 1.0
RESPONSE_WINDOW = 1.5
REST_INTERVAL = 1.0
ANTICIPATION_THRESHOLD = 0.1
DIGITS_DURATION = 2.0  # zobrazení číslic na začátku sady
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
DIGITS_HEIGHT = 80  # px
# Česká klávesnice: horní řada bez Shiftu píše tyto znaky; při vybavení se berou jako číslice
# (i velká písmena při Caps Lock). „+“ je i plus na numerické klávesnici (iohub obojí hlásí
# jako num_add), překlep tam zapíše 1; účastník ho vidí a může smazat.
CZECH_DIGIT_ROW = dict(zip("+ěščřžýáíé", "1234567890", strict=True))

# Plán startů
# Na podmínku a prodlevu (docs/experiment.md, „Plán startů“); podmínka = 2 bloky
GO_PER_FOREPERIOD = 9
NOGO_PER_FOREPERIOD = 3
MAX_NOGO_RUN = 2  # nejvýš tolik no-go startů za sebou v bloku
MAX_SHUFFLES = 10_000  # pojistka: pravidlo splní asi 80 % zamíchání, víc pokusů = chyba
BLOCK_LOADS = {"A": "low", "B": "high"}  # písmena v pořadí bloků ABBA / BAAB
SEED_MAX = 2**31  # seed sezení je náhodné celé číslo 0 … SEED_MAX - 1
# Zkrácený plán pro testy (uv run main.py --short): z každého bloku jen první sady
SHORT_FLAG = "--short"
SHORT_SETS_PER_BLOCK = 1

# Klávesnice (stejný backend na macOS i Windows, viz CLAUDE.md)
KEYBOARD_BACKEND = "iohub"

# Kolik varování o vypadlých snímcích PsychoPy zapíše do logu (výchozích 5 je na sezení málo)
DROPPED_FRAME_WARNINGS_MAX = 100_000

# Data
DATA_DIR_NAME = "data"
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
TEXT_HEIGHT = 40  # px
# Zpětná vazba v pauze: nad lampami (lampy sahají do y = -50, vlajka v pauze není)
FEEDBACK_Y = 60  # px
FEEDBACK_HEIGHT = 60  # px
PROMPT_Y = 120  # px, pozice řádků na obrazovce s nickem
INPUT_Y = 0
MESSAGE_Y = -120
CURSOR = "_"
TEXT_WRAP_SHARE = 0.8  # podíl šířky okna, na který se text zalomí
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
    "Účastník: {nick}    počítač: {machine}    data: {folder}\n\n"
    "Pořadí bloků: {block_order}    ({order_note})\n"
    "A = ABBA, B = BAAB\n\n"
    "Jazyk účastníka: {language_name}\n"
    "C = čeština, E = English\n\n"
    "Enter = začít sezení"
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
        "block_pause": "Pauza. Až budete připraveni, stiskněte mezerník.",
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
        "block_pause": "Break. When you are ready, press the space bar.",
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
SIM_ESCAPE_AT = 5  # uprostřed 2. sady: rozdělaná sada se nesmí zapsat
SIM_NICK = "sim"
SIM_LANGUAGE = "en"
# Klávesy, které simulace „napíše“ na úvodních obrazovkách: příliš krátký nick (chyba),
# Backspace, nick „sim“, přepnutí jazyka na EN, start sezení.
SIM_INTRO_KEYS = ("x", "return", "backspace", "s", "i", "m", "return", "e", "return")
# Simulace uloží obrázek první pauzy po každém typu výsledku (obsah okna PsychoPy,
# ne obrazovky). Na Retině je obrázek 2× zvětšený výřez středu okna (omezení
# getMovieFrame), dlouhý text proto vypadá useknutý; vzhled ověřuje ruční test.
SIM_SCREENS_SUFFIX = "_screens"
# Vybavení číslic v simulaci se střídá: správně, špatná poslední číslice, překlep opravený
# Backspacem, kratší odpověď (jen první číslice).
SIM_RECALL_CYCLE = ("correct", "wrong", "corrected", "short")
SIM_DIR_NAME = "sim"
# Simulace běží v menším okně uprostřed (jen pro ni, ostrý běh ho nedostane), aby nechala
# volnou obrazovku. Okno je aspoň tak velké, aby se vešly lampy i vlajka s okrajem.
SIM_WINDOW_MODE = "windowed"
SIM_WINDOW_SCALE = 0.4  # podíl velikosti displeje
SIM_WINDOW_MARGIN = 40  # px kolem podnětů
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
