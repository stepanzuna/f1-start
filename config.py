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

# Výsledky startu (docs/experiment.md, „Výsledky startu“); jump_start může nastat u obou typů
GO_OUTCOMES = ("jump_start", "anticipation", "go", "omission")
NOGO_OUTCOMES = ("jump_start", "commission", "inhibit")
OUTCOMES_WITH_RT = ("anticipation", "go", "commission")

# Design (docs/experiment.md, „Design“): zátěž a počet ostrých bloků (block 0 = testovací kolo)
LOADS = ("none", "low", "high")
N_BLOCKS = 4

# Plán startů
GO_PER_FOREPERIOD = 3
NOGO_PER_FOREPERIOD = 1

# Klávesnice (stejný backend na macOS i Windows, viz CLAUDE.md)
KEYBOARD_BACKEND = "iohub"

# Kolik varování o vypadlých snímcích PsychoPy zapíše do logu (výchozích 5 je na sezení málo)
DROPPED_FRAME_WARNINGS_MAX = 100_000

# Data
DATA_DIR_NAME = "data"
META_SUFFIX = "_meta.json"
LOG_SUFFIX = "_log.txt"
PLACEHOLDER_NICK = "test"  # do kroku 4 (zadání nicku v okně)
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
