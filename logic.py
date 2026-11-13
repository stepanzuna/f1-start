"""Čistá logika experimentu bez PsychoPy: start, plán, řádky dat, metadata a simulace."""

import itertools
import json
import random
import subprocess
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace

from config import (
    ANTICIPATION_THRESHOLD,
    FLAG_HEIGHT,
    FLAG_POS,
    FLAG_WIDTH,
    FOREPERIODS,
    GO_PER_FOREPERIOD,
    LAMP_RADIUS,
    LAMP_SPACING,
    LAMP_Y,
    LIGHT_INTERVAL,
    MACHINE_CODES,
    N_LAMPS,
    NOGO_PER_FOREPERIOD,
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
        # Pořadí bloků doplní krok 4, seed krok 7, hodnocení námahy krok 9.
        "block_order": None,
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


def session_data_dir(data_root: Path, simulated: bool) -> Path:
    """Složka pro data sezení: simulace do vlastní podsložky, mimo ostrá data."""
    return data_root / SIM_DIR_NAME if simulated else data_root


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
    """Simulovaný stisk se stejnými atributy, jaké program čte z KeyPress v PsychoPy."""

    name: str
    rt: float | None


class SimulatedKeyboard:
    """Falešná klávesnice pro simulaci: stiskne podle scénáře, čas počítá ve snímcích.

    Napodobuje tu část keyboard.Keyboard, kterou program používá: clearEvents() na začátku
    startu vezme další odpověď ze scénáře, clock.reset() (volané při zhasnutí) spustí
    měření reakce a getKeys() se volá jednou za snímek.
    """

    def __init__(self, scenario: list[str], rate: float) -> None:
        self._responses = iter(scenario)
        self._rate = rate
        self._response: str | None = None
        self._polls_since_clear = 0
        self._polls_since_reset: int | None = None
        self.clock = SimpleNamespace(reset=self._reset)

    def getBackend(self) -> str:
        """Název backendu do metadat."""
        return SIM_KEYBOARD_BACKEND

    def clearEvents(self) -> None:
        """Začátek startu: připraví další odpověď ze scénáře."""
        self._response = next(self._responses, None)
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
        self, keyList: list[str], waitRelease: bool = False
    ) -> list[SimulatedKeyPress]:
        """Jedno čtení klávesnice za snímek, stejné volání jako u keyboard.Keyboard."""
        press = self._due_press()
        self._polls_since_clear += 1
        if self._polls_since_reset is not None:
            self._polls_since_reset += 1
        if press is None or press.name not in keyList:
            return []
        self._response = None
        return [press]
