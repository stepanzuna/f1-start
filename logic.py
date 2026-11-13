"""Čistá logika experimentu bez PsychoPy: popis startu, plán startů a řádky dat."""

import json
import random
import subprocess
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from config import (
    ANTICIPATION_THRESHOLD,
    FOREPERIODS,
    GO_PER_FOREPERIOD,
    LIGHT_INTERVAL,
    MACHINE_CODES,
    NOGO_PER_FOREPERIOD,
    RESPONSE_WINDOW,
    REST_INTERVAL,
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
