"""Čistá logika experimentu bez PsychoPy: start, plán, řádky dat, metadata a simulace."""

import itertools
import json
import random
import subprocess
from collections import deque
from collections.abc import Callable
from dataclasses import dataclass, replace
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace

from config import (
    ANTICIPATION_THRESHOLD,
    BACKSPACE_KEY,
    BLOCK_ORDER_KEYS,
    BLOCK_ORDERS,
    ENTER_KEYS,
    FLAG_HEIGHT,
    FLAG_POS,
    FLAG_WIDTH,
    FOREPERIODS,
    GO_PER_FOREPERIOD,
    LAMP_RADIUS,
    LAMP_SPACING,
    LAMP_Y,
    LANGUAGE_KEYS,
    LIGHT_INTERVAL,
    MACHINE_CODES,
    META_SUFFIX,
    N_LAMPS,
    NICK_CHARS,
    NICK_EXISTS,
    NICK_INVALID,
    NICK_MAX_LENGTH,
    NICK_MIN_LENGTH,
    NOGO_PER_FOREPERIOD,
    ORDER_AUTO,
    ORDER_MANUAL,
    PILOT_PREFIX,
    RESPONSE_WINDOW,
    REST_INTERVAL,
    SIM_DIR_NAME,
    SIM_EARLY_PRESS,
    SIM_ESCAPE_AT,
    SIM_ESCAPE_FLAG,
    SIM_FLAG,
    SIM_GO_CYCLE,
    SIM_KEYBOARD_BACKEND,
    SIM_NOGO_CYCLE,
    SIM_PRESS_RT,
    SIM_WINDOW_MARGIN,
    SIM_WINDOW_SCALE,
    TEST_PREFIX,
)


@dataclass
class Start:
    """Jeden start v plánu sezení."""

    foreperiod: float
    is_nogo: bool
    load: str
    block: int
    set_index: int
    start_in_set: int


def make_plan() -> list[Start]:
    """Vytvoří zamíchaný plán startů, každá prodleva s daným počtem go a no-go."""
    plan = []
    for foreperiod in FOREPERIODS:
        kinds = [False] * GO_PER_FOREPERIOD + [True] * NOGO_PER_FOREPERIOD
        for is_nogo in kinds:
            # Zástupné hodnoty, skutečnou zátěž, bloky a sady doplní krok 7.
            plan.append(
                Start(
                    foreperiod=foreperiod,
                    is_nogo=is_nogo,
                    load="none",
                    block=0,
                    set_index=0,
                    start_in_set=0,
                )
            )
    random.shuffle(plan)
    return plan


def classify_press(rt: float, is_nogo: bool) -> str:
    """Vyhodnotí stisk v okně odpovědi v pořadí podle docs/experiment.md."""
    if rt < 0:
        return "jump_start"
    if is_nogo:
        return "commission"
    if rt < ANTICIPATION_THRESHOLD:
        return "anticipation"
    return "go"


def outcome_without_press(is_nogo: bool) -> str:
    """Výsledek startu, ve kterém do konce okna odpovědi nikdo nestiskl."""
    return "inhibit" if is_nogo else "omission"


def machine_code(platform: str) -> str:
    """Převede `sys.platform` na kód stroje do dat ("mac" nebo "win")."""
    if platform not in MACHINE_CODES:
        raise ValueError(
            f"Nepodporovaný systém {platform!r}, povolené: {MACHINE_CODES}"
        )
    return MACHINE_CODES[platform]


def make_data_path(
    data_dir: Path, nick: str, machine: str, started_at: datetime
) -> Path:
    """Sestaví cestu k CSV ve tvaru {nick}_{stroj}_{YYYY-MM-DD_HHMM}.csv."""
    return data_dir / f"{nick}_{machine}_{started_at:%Y-%m-%d_%H%M}.csv"


def make_row(
    participant: str,
    machine: str,
    start: Start,
    trial_index: int,
    outcome: str,
    rt: float | None,
    dropped_frames: int,
    written_at: datetime,
) -> dict[str, object]:
    """Sestaví jeden řádek CSV (jeden start) ve sloupcích podle CSV_COLUMNS."""
    return {
        "participant": participant,
        "machine": machine,
        "phase": "practice" if start.block == 0 else "main",
        "block": start.block,
        "load": start.load,
        "set_index": start.set_index,
        "start_in_set": start.start_in_set,
        "trial_index": trial_index,
        "foreperiod_s": start.foreperiod,
        "is_nogo": start.is_nogo,
        "outcome": outcome,
        "rt_ms": "" if rt is None else round(rt * 1000, 1),
        # Číslice doplní krok 6 (paměťová zátěž).
        "digits_shown": "",
        "digits_typed": "",
        "recall_correct": "",
        "dropped_frames": dropped_frames,
        "timestamp": written_at.isoformat(timespec="seconds"),
    }


def companion_path(csv_path: Path, suffix: str) -> Path:
    """Odvodí z cesty k CSV cestu k souboru téhož sezení (meta, log)."""
    return csv_path.with_name(csv_path.stem + suffix)


def git_commit(repo_dir: Path) -> str:
    """Vrátí krátký hash commitu, s příponou -dirty při necommitnutých změnách.

    Počítají se i nové nesledované soubory (data/ je v .gitignore, nepočítá se).
    """
    try:
        head = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=repo_dir,
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()
        changes = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=repo_dir,
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return "unknown"
    return f"{head}-dirty" if changes else head


def make_meta(
    participant: str,
    machine: str,
    started_at: datetime,
    environment: dict[str, str],
    frame_rate: float,
    window_mode: str,
    window_size: tuple[int, int],
    keyboard_backend: str,
    planned_starts: int,
    block_order: str,
    language: str,
    simulated: bool,
) -> dict[str, object]:
    """Sestaví metadata sezení; dokud sezení řádně neskončí, je označené jako přerušené."""
    return {
        "participant": participant,
        "machine": machine,
        **environment,
        "started_at": started_at.isoformat(timespec="seconds"),
        "ended_at": None,
        "aborted": True,
        "simulated": simulated,
        "block_order": block_order,
        "language": language,
        # Seed doplní krok 7, hodnocení námahy krok 9.
        "seed": None,
        "effort_ratings": [],
        "planned_starts": planned_starts,
        "frame_rate_hz": round(frame_rate, 3),
        "window_mode": window_mode,
        "window_size_px": list(window_size),
        "keyboard_backend": keyboard_backend,
        "timing_s": {
            "LIGHT_INTERVAL": LIGHT_INTERVAL,
            "FOREPERIODS": list(FOREPERIODS),
            "RESPONSE_WINDOW": RESPONSE_WINDOW,
            "REST_INTERVAL": REST_INTERVAL,
            "ANTICIPATION_THRESHOLD": ANTICIPATION_THRESHOLD,
        },
        "dropped_frames_total": None,
    }


def finish_meta(
    meta: dict[str, object], ended_at: datetime, dropped_frames_total: int
) -> dict[str, object]:
    """Vrátí kopii metadat označenou jako řádně dokončené sezení."""
    return {
        **meta,
        "ended_at": ended_at.isoformat(timespec="seconds"),
        "aborted": False,
        "dropped_frames_total": dropped_frames_total,
    }


def write_meta(path: Path, meta: dict[str, object]) -> None:
    """Uloží metadata do JSON přes dočasný soubor, aby pád nenechal soubor napůl zapsaný."""
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(
        json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    temporary.replace(path)


def parse_args(args: list[str]) -> tuple[bool, int | None]:
    """Přečte argumenty příkazové řádky: (simulace, start s Escapem nebo None).

    Neznámý argument (např. překlep --simm) je chyba, aby se omylem nespustil ostrý běh.
    """
    unknown = [arg for arg in args if arg not in (SIM_FLAG, SIM_ESCAPE_FLAG)]
    if unknown:
        raise ValueError(
            f"Neznámý argument {unknown[0]!r}. Povolené: {SIM_FLAG}, {SIM_ESCAPE_FLAG}."
        )
    escape_at = SIM_ESCAPE_AT if SIM_ESCAPE_FLAG in args else None
    return bool(args), escape_at


def session_data_dir(data_root: Path, simulated: bool, nick: str) -> Path:
    """Složka pro data sezení: simulace, pilot a testy do podsložek, mimo ostrá data."""
    if simulated:
        return data_root / SIM_DIR_NAME
    for prefix in (PILOT_PREFIX, TEST_PREFIX):
        if nick.startswith(prefix):
            return data_root / prefix
    return data_root


def edit_text(text: str, name: str, char: str, allowed: str, max_length: int) -> str:
    """Upraví psaný text jedním stiskem: Backspace maže, povolený znak se připíše."""
    if name == BACKSPACE_KEY:
        return text[:-1]
    if len(char) == 1 and char in allowed and len(text) < max_length:
        return text + char
    return text


def is_valid_nick(nick: str) -> bool:
    """Nick: 2–16 znaků, malá písmena a–z, číslice, - a _ (docs/experiment.md)."""
    length_ok = NICK_MIN_LENGTH <= len(nick) <= NICK_MAX_LENGTH
    return length_ok and all(char in NICK_CHARS for char in nick)


def genuine_presses(keys: list, still_down: object | None) -> list:
    """Vynechá „fantomové“ stisky, které PsychoPy vyrobí z puštění klávesy po Shiftu.

    Puštění se páruje se stiskem podle napsaného znaku. Když Shift pustíte dřív než
    klávesu (Shift+minus = „_“, puštění = „-“), pár se nenajde a vznikne nový stisk.
    Skutečný stisk je mezi drženými klávesami (still_down) nebo už má délku stisku.
    still_down=None (simulace) = všechny stisky jsou skutečné.
    """
    if still_down is None:
        return keys
    return [
        key
        for key in keys
        if getattr(key, "duration", None) is not None
        or any(down is key for down in still_down)
    ]


@dataclass(frozen=True)
class NickInput:
    """Stav obrazovky s nickem: napsaný text, hláška a jestli se čeká na potvrzení."""

    text: str = ""
    message: str = ""
    awaiting_confirmation: bool = False
    done: bool = False


def nick_input_key(
    state: NickInput, name: str, char: str, exists: Callable[[str], bool]
) -> NickInput:
    """Zpracuje jednu klávesu na obrazovce s nickem a vrátí nový stav.

    Enter ověří nick; existující nick chce druhý Enter. Jakákoli úprava textu
    (i Backspace = „opravit“) hlášku i čekání na potvrzení zruší.
    """
    if name in ENTER_KEYS:
        if not is_valid_nick(state.text):
            return replace(state, message=NICK_INVALID, awaiting_confirmation=False)
        if state.awaiting_confirmation or not exists(state.text):
            return replace(state, done=True)
        return replace(
            state,
            message=NICK_EXISTS.format(nick=state.text),
            awaiting_confirmation=True,
        )
    text = edit_text(state.text, name, char, NICK_CHARS, NICK_MAX_LENGTH)
    if text == state.text:
        return state  # Shift, Caps Lock apod. hlášku ani potvrzení nezruší
    return NickInput(text=text)


def nick_from_filename(name: str) -> str | None:
    """Vytáhne nick z názvu souboru {nick}_{stroj}_{YYYY-MM-DD}_{HHMM}…; nick smí mít „_“."""
    parts = Path(name).stem.split("_")
    if len(parts) < 4 or parts[-3] not in MACHINE_CODES.values():
        return None
    return "_".join(parts[:-3])


def nick_exists(data_dir: Path, nick: str) -> bool:
    """Zjistí, jestli ve složce dat už je sezení se stejným nickem."""
    return any(nick_from_filename(path.name) == nick for path in data_dir.glob("*.csv"))


def count_completed_sessions(data_dir: Path, machine: str) -> int:
    """Spočítá dokončená ostrá sezení tohoto počítače (meta s aborted = false) v data/.

    Nepočítá pilot, testy ani simulace (ani kdyby omylem ležely přímo v data/) a data
    zkopírovaná z jiného počítače.
    """
    count = 0
    for meta_path in data_dir.glob("*" + META_SUFFIX):
        try:
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        simulated = bool(meta.get("simulated"))
        nick = str(meta.get("participant", ""))
        is_main = session_data_dir(data_dir, simulated, nick) == data_dir
        if meta.get("aborted") is False and is_main and meta.get("machine") == machine:
            count += 1
    return count


def assign_block_order(completed_sessions: int) -> str:
    """Střídání pořadí bloků na tomto počítači: sudý počet → ABBA, lichý → BAAB."""
    return BLOCK_ORDERS[completed_sessions % len(BLOCK_ORDERS)]


def settings_order_note(block_order: str, auto_order: str, completed: int) -> str:
    """Poznámka k pořadí bloků: automatické, nebo ručně přepsané."""
    if block_order == auto_order:
        return ORDER_AUTO.format(completed=completed)
    return ORDER_MANUAL.format(auto_order=auto_order)


def apply_settings_key(name: str, block_order: str, language: str) -> tuple[str, str]:
    """Klávesa na obrazovce nastavení: A/B mění pořadí bloků, C/E jazyk účastníka."""
    return (
        BLOCK_ORDER_KEYS.get(name, block_order),
        LANGUAGE_KEYS.get(name, language),
    )


def make_sim_scenario(plan: list[Start], escape_at: int | None = None) -> list[str]:
    """Přiřadí každému startu typ odpovědi; go a no-go starty se střídají dokola zvlášť.

    S escape_at (pořadí startu od 1) se v tom startu stiskne Escape a sezení se přeruší.
    """
    go_responses = itertools.cycle(SIM_GO_CYCLE)
    nogo_responses = itertools.cycle(SIM_NOGO_CYCLE)
    scenario = [
        next(nogo_responses if start.is_nogo else go_responses) for start in plan
    ]
    if escape_at is not None:
        scenario[escape_at - 1] = "escape"
    return scenario


def sim_window_size(screen: tuple[int, int], pixel_ratio: float) -> tuple[int, int]:
    """Velikost okna simulace: podíl displeje, ale aspoň tolik, aby se vešly všechny podněty.

    Okno se zadává v bodech displeje, podněty jsou v pixelech; pixel_ratio je počet pixelů
    na bod (Retina 2, jinak 1).
    """
    half_width = max(FLAG_WIDTH / 2, (N_LAMPS - 1) / 2 * LAMP_SPACING + LAMP_RADIUS)
    half_height = max(FLAG_POS[1] + FLAG_HEIGHT / 2, abs(LAMP_Y) + LAMP_RADIUS)
    needed = (
        round(2 * (half_width + SIM_WINDOW_MARGIN) / pixel_ratio),
        round(2 * (half_height + SIM_WINDOW_MARGIN) / pixel_ratio),
    )
    return tuple(
        min(side, max(round(side * SIM_WINDOW_SCALE), minimum))
        for side, minimum in zip(screen, needed, strict=True)
    )


def expected_outcome(response: str, is_nogo: bool) -> str:
    """Výsledek, který má program vyhodnotit pro danou simulovanou odpověď."""
    if response == "early":
        return "jump_start"
    if response == "none":
        return outcome_without_press(is_nogo)
    return classify_press(SIM_PRESS_RT[response], is_nogo)


@dataclass
class SimulatedKeyPress:
    """Simulovaný stisk se stejnými atributy, jaké program čte z KeyPress v PsychoPy.

    name je název klávesy (např. "return"), code napsaný znak (jako char z iohub).
    """

    name: str
    rt: float | None
    code: str = ""


def sim_key(name: str) -> SimulatedKeyPress:
    """Simulovaný stisk klávesy na obrazovce s textem (písmeno, Enter, Backspace)."""
    code = name if len(name) == 1 else {"return": "\n"}.get(name, "")
    return SimulatedKeyPress(name, None, code)


class SimulatedKeyboard:
    """Falešná klávesnice pro simulaci: stiskne podle scénáře, čas počítá ve snímcích.

    Napodobuje tu část keyboard.Keyboard, kterou program používá: první getKeys() s mezerníkem
    po clearEvents() (začátek startu) vezme další odpověď ze scénáře, clock.reset() (volané
    při zhasnutí) spustí měření reakce, getKeys() bez keyList vrací klávesy napsané
    na obrazovkách s textem. getKeys() se volá jednou za snímek.
    """

    def __init__(
        self, scenario: list[str], rate: float, typed_keys: list[str] | None = None
    ) -> None:
        self._responses = iter(scenario)
        self._typed = deque(typed_keys or [])
        self._rate = rate
        self._response: str | None = None
        self._started = False
        self._polls_since_clear = 0
        self._polls_since_reset: int | None = None
        self.clock = SimpleNamespace(reset=self._reset)

    def getBackend(self) -> str:
        """Název backendu do metadat."""
        return SIM_KEYBOARD_BACKEND

    def clearEvents(self) -> None:
        """Smaže čekající stisky; další start si vezme novou odpověď ze scénáře."""
        self._response = None
        self._started = False
        self._polls_since_clear = 0
        self._polls_since_reset = None

    def _reset(self) -> None:
        """Zhasnutí lamp: od teď se měří reakční čas."""
        self._polls_since_reset = 0

    def _due_press(self) -> SimulatedKeyPress | None:
        """Vrátí stisk, pokud podle scénáře v tomto snímku nastal, jinak None."""
        if self._response in (None, "none"):
            return None
        if self._response == "escape":
            return SimulatedKeyPress("escape", None)
        if self._response == "early":
            before_reset = self._polls_since_reset is None
            if before_reset and self._polls_since_clear / self._rate >= SIM_EARLY_PRESS:
                return SimulatedKeyPress("space", None)
            return None
        rt = SIM_PRESS_RT[self._response]
        if (
            self._polls_since_reset is not None
            and self._polls_since_reset / self._rate >= rt
        ):
            return SimulatedKeyPress("space", rt)
        return None

    def getKeys(
        self, keyList: list[str] | None = None, waitRelease: bool = False
    ) -> list[SimulatedKeyPress]:
        """Jedno čtení klávesnice za snímek, stejné volání jako u keyboard.Keyboard.

        Bez keyList (obrazovky s textem) vrátí další napsanou klávesu. S mezerníkem
        v keyList jde o start: první čtení po clearEvents vezme odpověď ze scénáře.
        Proto obrazovky mimo start čtou klávesy vždy bez keyList (viz CLAUDE.md).
        """
        if keyList is None:
            return [sim_key(self._typed.popleft())] if self._typed else []
        if "space" in keyList and not self._started:
            self._response = next(self._responses, None)
            self._started = True
        press = self._due_press()
        self._polls_since_clear += 1
        if self._polls_since_reset is not None:
            self._polls_since_reset += 1
        if press is None or press.name not in keyList:
            return []
        self._response = None
        return [press]
