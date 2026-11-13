"""Kontrola dat jednoho sezení (CSV, metadata a log) bez PsychoPy.

Použití: uv run check_data.py [data/<soubor>.csv]
Bez argumentu zkontroluje nejnovější CSV ve složce data/. Při problému skončí s kódem 1,
varování (např. vypadlé snímky) kód nemění.
"""

import csv
import json
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path

from config import (
    ANTICIPATION_THRESHOLD,
    CSV_COLUMNS,
    DATA_DIR_NAME,
    FOREPERIODS,
    GO_OUTCOMES,
    KEYBOARD_BACKEND,
    LOADS,
    LOG_SUFFIX,
    MACHINE_CODES,
    META_SUFFIX,
    N_BLOCKS,
    NOGO_OUTCOMES,
    OUTCOMES_WITH_RT,
    RESPONSE_WINDOW,
    SIM_DIR_NAME,
    SIM_PRESS_RT,
    WINDOW_MODES,
)
from logic import companion_path, expected_outcome

REQUIRED_META_KEYS = (
    "participant",
    "machine",
    "platform",
    "python_version",
    "psychopy_version",
    "git_commit",
    "started_at",
    "ended_at",
    "aborted",
    "simulated",
    "block_order",
    "seed",
    "effort_ratings",
    "planned_starts",
    "frame_rate_hz",
    "window_mode",
    "window_size_px",
    "keyboard_backend",
    "timing_s",
    "dropped_frames_total",
)
BOOL_TEXTS = ("True", "False")
SIM_RESPONSES = ("early", "none", "escape", *SIM_PRESS_RT)
BLOCK_TEXTS = tuple(str(block) for block in range(N_BLOCKS + 1))
MS_PER_S = 1000


def parse_float(text: str) -> float | None:
    """Převede text na číslo, při neplatném textu vrátí None."""
    try:
        return float(text)
    except ValueError:
        return None


def dropped_frames(row: dict[str, str]) -> int:
    """Vypadlé snímky v řádku, neplatná hodnota se počítá jako 0 (hlásí ji check_row)."""
    value = row["dropped_frames"]
    return int(value) if value.isdigit() else 0


def is_complete(row: dict[str, str | None]) -> bool:
    """Pozná úplný řádek; oříznutý řádek (např. po pádu) má hodnoty None."""
    return None not in row and all(value is not None for value in row.values())


def check_header(header: list[str]) -> list[str]:
    """Ověří, že CSV má přesně sloupce ze specifikace ve správném pořadí."""
    if tuple(header) != CSV_COLUMNS:
        return [f"sloupce CSV {header} neodpovídají specifikaci {list(CSV_COLUMNS)}"]
    return []


def check_rt(outcome: str, rt_text: str) -> list[str]:
    """Ověří reakční čas: vyplněný jen u výsledků s reakcí a v mezích podle výsledku.

    Výsledek se určuje z nezaokrouhleného času, uložené rt_ms je zaokrouhlené na 0,1 ms.
    Proto anticipation smí mít rt_ms rovné prahu (např. 0,09996 s → 100.0 ms).
    """
    if outcome not in OUTCOMES_WITH_RT:
        return [] if rt_text == "" else [f"{outcome} nemá mít rt_ms, má {rt_text}"]
    rt_ms = parse_float(rt_text)
    if rt_ms is None:
        return [f"{outcome} má mít číselné rt_ms, má {rt_text!r}"]
    threshold_ms = ANTICIPATION_THRESHOLD * MS_PER_S
    problems = []
    if not 0 <= rt_ms <= RESPONSE_WINDOW * MS_PER_S:
        problems.append(f"rt_ms {rt_ms} je mimo okno odpovědi")
    if outcome == "anticipation" and rt_ms > threshold_ms:
        problems.append(f"anticipation s rt_ms {rt_ms} > {threshold_ms}")
    if outcome == "go" and rt_ms < threshold_ms:
        problems.append(f"go s rt_ms {rt_ms} < {threshold_ms}")
    return problems


def check_row(
    row: dict[str, str], expected_index: int, meta: dict[str, object]
) -> list[str]:
    """Zkontroluje jeden úplný řádek CSV a vrátí seznam problémů (prázdný = v pořádku)."""
    problems = []
    if row["participant"] != meta.get("participant"):
        problems.append(f"participant {row['participant']!r} nesedí s meta")
    if (
        row["machine"] != meta.get("machine")
        or row["machine"] not in MACHINE_CODES.values()
    ):
        problems.append(f"machine {row['machine']!r} nesedí s meta nebo není mac/win")
    if row["trial_index"] != str(expected_index):
        problems.append(f"trial_index {row['trial_index']}, čekáno {expected_index}")
    if row["is_nogo"] not in BOOL_TEXTS:
        problems.append(f"is_nogo {row['is_nogo']!r} není True/False")
    allowed = NOGO_OUTCOMES if row["is_nogo"] == "True" else GO_OUTCOMES
    if row["outcome"] not in allowed:
        problems.append(
            f"outcome {row['outcome']!r} nepatří k is_nogo={row['is_nogo']}"
        )
    else:
        problems.extend(check_rt(row["outcome"], row["rt_ms"]))
    if parse_float(row["foreperiod_s"]) not in FOREPERIODS:
        problems.append(f"foreperiod_s {row['foreperiod_s']!r} není schválená prodleva")
    if row["load"] not in LOADS:
        problems.append(f"load {row['load']!r} není {'/'.join(LOADS)}")
    if row["block"] not in BLOCK_TEXTS:
        problems.append(f"block {row['block']!r} není 0–{N_BLOCKS}")
    expected_phase = "practice" if row["block"] == "0" else "main"
    if row["phase"] != expected_phase:
        problems.append(f"phase {row['phase']!r} nesedí k block {row['block']}")
    if not row["dropped_frames"].isdigit():
        problems.append(f"dropped_frames {row['dropped_frames']!r} není celé číslo ≥ 0")
    try:
        datetime.fromisoformat(row["timestamp"])
    except ValueError:
        problems.append(f"timestamp {row['timestamp']!r} není ISO 8601")
    # set_index a start_in_set jsou do kroku 7 zástupně 0, kontrolu doplní krok 7.
    return [f"řádek {expected_index}: {problem}" for problem in problems]


def check_meta(meta: dict[str, object], rows: list[dict[str, str]]) -> list[str]:
    """Ověří metadata a jejich soulad s (úplnými) řádky CSV."""
    problems = [
        f"meta: chybí klíč {key}" for key in REQUIRED_META_KEYS if key not in meta
    ]
    if problems:
        return problems
    planned = meta["planned_starts"]
    if meta["aborted"]:
        if meta["ended_at"] is not None:
            problems.append("meta: přerušené sezení má ended_at")
        if len(rows) > planned:
            problems.append(
                f"přerušené sezení má {len(rows)} řádků, plán jen {planned}"
            )
        return problems
    if len(rows) != planned:
        problems.append(f"dokončené sezení má {len(rows)} řádků, plán má {planned}")
    if meta["ended_at"] is None:
        problems.append("meta: dokončené sezení nemá ended_at")
    dropped_in_starts = sum(dropped_frames(row) for row in rows)
    if not isinstance(meta["dropped_frames_total"], int):
        problems.append("meta: dropped_frames_total není celé číslo")
    elif meta["dropped_frames_total"] < dropped_in_starts:
        problems.append(
            f"meta: dropped_frames_total {meta['dropped_frames_total']} je menší než součet "
            f"ve startech {dropped_in_starts}"
        )
    return problems


def check_files(csv_path: Path, meta: dict[str, object]) -> list[str]:
    """Ověří název a umístění souboru proti meta a existenci logu."""
    problems = []
    in_sim_dir = csv_path.parent.name == SIM_DIR_NAME
    if bool(meta.get("simulated")) != in_sim_dir:
        problems.append(
            f"simulated={meta.get('simulated')}, ale soubor leží v {csv_path.parent.name}/ "
            f"(simulace patří do {SIM_DIR_NAME}/, nic jiného tam)"
        )
    if not meta.get("simulated"):
        if meta.get("keyboard_backend") != KEYBOARD_BACKEND:
            problems.append(f"ostré sezení nemá klávesnici {KEYBOARD_BACKEND}")
        if meta.get("window_mode") not in WINDOW_MODES:
            problems.append(f"ostré sezení má režim okna {meta.get('window_mode')!r}")
    prefix = f"{meta.get('participant')}_{meta.get('machine')}_"
    if not csv_path.name.startswith(prefix):
        problems.append(f"název {csv_path.name} nezačíná {prefix}")
    if not companion_path(csv_path, LOG_SUFFIX).exists():
        problems.append(f"chybí log {csv_path.stem}{LOG_SUFFIX}")
    return problems


def check_simulation(meta: dict[str, object], rows: list[dict[str, str]]) -> list[str]:
    """U simulace porovná výsledek a reakční čas každého startu s předpovědí scénáře."""
    if not meta.get("simulated"):
        return []
    scenario = meta.get("sim_scenario")
    if not isinstance(scenario, list) or len(scenario) != meta.get("planned_starts"):
        return ["meta: simulace nemá scénář pro každý plánovaný start"]
    unknown = sorted(
        {response for response in scenario if response not in SIM_RESPONSES}
    )
    if unknown:
        return [f"meta: neznámé odpovědi ve scénáři simulace {unknown}"]
    problems = []
    if "escape" in scenario:
        escape_at = scenario.index("escape") + 1
        if not meta["aborted"] or len(rows) != escape_at - 1:
            problems.append(
                f"simulace s Escapem ve startu {escape_at} má mít aborted a {escape_at - 1} "
                f"řádků, má aborted={meta['aborted']} a {len(rows)} řádků"
            )
        scenario = scenario[: escape_at - 1]
    for index, (row, response) in enumerate(zip(rows, scenario, strict=False), start=1):
        expected = expected_outcome(response, row["is_nogo"] == "True")
        if row["outcome"] != expected:
            problems.append(
                f"řádek {index}: simulace {response!r} čekala {expected}, "
                f"program vyhodnotil {row['outcome']}"
            )
        elif expected in OUTCOMES_WITH_RT:
            expected_rt = str(round(SIM_PRESS_RT[response] * MS_PER_S, 1))
            if row["rt_ms"] != expected_rt:
                problems.append(
                    f"řádek {index}: simulace čekala rt_ms {expected_rt}, je {row['rt_ms']}"
                )
    return problems


def dropped_frame_warnings(rows: list[dict[str, str]]) -> list[str]:
    """Varování pro starty s vypadlými snímky (časování mohlo být nepřesné)."""
    return [
        f"start {row['trial_index']}: {dropped_frames(row)} vypadlých snímků"
        for row in rows
        if dropped_frames(row) > 0
    ]


def summarize(meta: dict[str, object], rows: list[dict[str, str]]) -> str:
    """Krátké shrnutí sezení pro výpis."""
    outcomes = Counter(row["outcome"] for row in rows)
    go_rts = [
        rt
        for row in rows
        if row["outcome"] == "go" and (rt := parse_float(row["rt_ms"])) is not None
    ]
    mean_go = f"{sum(go_rts) / len(go_rts):.1f} ms" if go_rts else "–"
    session = (
        f"sezení: {meta.get('participant')} / {meta.get('machine')}, "
        f"aborted={meta.get('aborted')}, simulated={meta.get('simulated')}, "
        f"commit {meta.get('git_commit')}, klávesnice {meta.get('keyboard_backend')}"
    )
    window = (
        f"okno: {meta.get('window_mode')} {meta.get('window_size_px')}, "
        f"frekvence {meta.get('frame_rate_hz')} Hz"
    )
    starts = (
        f"startů: {len(rows)} z {meta.get('planned_starts')}, "
        f"výsledky: {dict(sorted(outcomes.items()))}"
    )
    timing = (
        f"průměrné RT go: {mean_go}, vypadlé snímky ve startech: "
        f"{sum(dropped_frames(row) for row in rows)}, "
        f"celkem: {meta.get('dropped_frames_total')}"
    )
    return f"{session}\n{window}\n{starts}\n{timing}"


def check_session(csv_path: Path) -> tuple[str, list[str], list[str]]:
    """Načte data jednoho sezení a vrátí (shrnutí, problémy, varování)."""
    meta_path = companion_path(csv_path, META_SUFFIX)
    if not meta_path.exists():
        return "", [f"chybí metadata {meta_path.name}"], []
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    with csv_path.open(newline="", encoding="utf-8") as data_file:
        reader = csv.DictReader(data_file)
        problems = check_header(list(reader.fieldnames or []))
        if problems:
            return "", problems, []
        all_rows = list(reader)
    rows = []
    for index, row in enumerate(all_rows, start=1):
        if is_complete(row):
            rows.append(row)
            problems.extend(check_row(row, index, meta))
        else:
            problems.append(
                f"řádek {index}: neúplný (oříznutý zápis?), nekontroluje se"
            )
    problems.extend(check_meta(meta, rows))
    problems.extend(check_files(csv_path, meta))
    problems.extend(check_simulation(meta, rows))
    return summarize(meta, rows), problems, dropped_frame_warnings(rows)


def latest_csv(data_dir: Path) -> Path:
    """Najde nejnovější CSV ve složce dat (i v podsložkách sim/ a pilot/)."""
    csv_files = sorted(data_dir.rglob("*.csv"), key=lambda path: path.stat().st_mtime)
    if not csv_files:
        sys.exit(f"Ve složce {data_dir} není žádné CSV.")
    return csv_files[-1]


def main() -> None:
    if len(sys.argv) > 1:
        csv_path = Path(sys.argv[1])
    else:
        csv_path = latest_csv(Path(__file__).parent / DATA_DIR_NAME)
    summary, problems, warnings = check_session(csv_path)
    print(csv_path.name)
    if summary:
        print(summary)
    if warnings:
        print(f"\nVAROVÁNÍ ({len(warnings)}):")
        print("\n".join(f"- {warning}" for warning in warnings))
    if problems:
        print(f"\nPROBLÉMY ({len(problems)}):")
        print("\n".join(f"- {problem}" for problem in problems))
        sys.exit(1)
    print("\nOK: data odpovídají specifikaci.")


if __name__ == "__main__":
    main()
