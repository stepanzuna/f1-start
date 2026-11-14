"""Kontrola dat jednoho sezení (CSV, metadata a log) bez PsychoPy.

Použití: uv run check_data.py [data/<soubor>.csv]
Bez argumentu zkontroluje nejnovější CSV ve složce data/. Při problému skončí s kódem 1,
varování (např. vypadlé snímky) kód nemění.
"""

import csv
import itertools
import json
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path

from config import (
    ANTICIPATION_THRESHOLD,
    BLOCK_ORDERS,
    CSV_COLUMNS,
    DATA_DIR_NAME,
    DIGITS_PER_LOAD,
    FOREPERIODS,
    GO_OUTCOMES,
    KEYBOARD_BACKEND,
    LANGUAGES,
    LOADS,
    LOG_SUFFIX,
    MACHINE_CODES,
    META_SUFFIX,
    N_BLOCKS,
    NOGO_OUTCOMES,
    OUTCOMES_WITH_RT,
    PILOT_PREFIX,
    PRACTICE_BLOCK,
    RESPONSE_WINDOW,
    SIM_DIR_NAME,
    SIM_LANGUAGE,
    SIM_NICK,
    SIM_PRESS_RT,
    STARTS_PER_SET,
    TEST_PREFIX,
    WINDOW_MODES,
)
from logic import (
    Start,
    build_practice,
    build_session,
    companion_path,
    is_valid_nick,
    session_data_dir,
    short_plan_allowed,
)
from simulation import (
    expected_outcome,
    sim_recall_answer,
    sim_sequence,
    starts_written_before,
)

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
    "language",
    "seed",
    "short",
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
SUBDIRS = (SIM_DIR_NAME, PILOT_PREFIX, TEST_PREFIX)
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
    rows = [row for row in rows if row["block"] != str(PRACTICE_BLOCK)]
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
    simulated = bool(meta.get("simulated"))
    expected = session_data_dir(Path(), simulated, str(meta.get("participant"))).name
    actual = csv_path.parent.name if csv_path.parent.name in SUBDIRS else ""
    if actual != expected:
        problems.append(
            f"soubor leží v {actual or 'data'}/, ale patří do {expected or 'data'}/ "
            f"(simulace patří do {SIM_DIR_NAME}/, pilot a testy podle nicku)"
        )
    if not is_valid_nick(str(meta.get("participant"))):
        problems.append(f"meta: nick {meta.get('participant')!r} nemá platný formát")
    if meta.get("language") not in LANGUAGES:
        problems.append(
            f"meta: jazyk {meta.get('language')!r} není {'/'.join(LANGUAGES)}"
        )
    if meta.get("block_order") not in BLOCK_ORDERS:
        problems.append(f"meta: pořadí bloků {meta.get('block_order')!r} není platné")
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
    if (
        not isinstance(meta.get("seed"), int)
        or meta.get("block_order") not in BLOCK_ORDERS
    ):
        return ["meta: simulace bez seedu nebo pořadí bloků"]
    sequence, _, _ = sim_sequence(
        str(meta["block_order"]), int(meta["seed"]), bool(meta.get("short"))
    )
    if not isinstance(scenario, list) or len(scenario) != len(sequence):
        return [
            "meta: simulace nemá scénář pro každý start (testovací kola i ostrá část)"
        ]
    unknown = sorted(
        {response for response in scenario if response not in SIM_RESPONSES}
    )
    if unknown:
        return [f"meta: neznámé odpovědi ve scénáři simulace {unknown}"]
    problems = []
    if (meta.get("participant"), meta.get("language")) != (SIM_NICK, SIM_LANGUAGE):
        problems.append(
            f"simulace měla napsat nick {SIM_NICK!r} a zvolit jazyk {SIM_LANGUAGE!r}, "
            f"v meta je {meta.get('participant')!r} a {meta.get('language')!r}"
        )
    if "escape" in scenario:
        escape_at = scenario.index("escape") + 1
        # Zapisuje se po sadě (část 1 testovacího kola po startu), rozdělaná se nezapíše.
        expected_rows = starts_written_before(sequence, escape_at)
        if not meta["aborted"] or len(rows) != expected_rows:
            problems.append(
                f"simulace s Escapem ve startu {escape_at} má mít aborted a {expected_rows} "
                f"řádků, má aborted={meta['aborted']} a {len(rows)} řádků"
            )
        scenario = scenario[:expected_rows]
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


def expected_row_values(start: Start, digits: str) -> dict[str, object]:
    """Hodnoty sloupců, které určuje plán (pro porovnání s CSV)."""
    return {
        "foreperiod_s": start.foreperiod,
        "is_nogo": str(start.is_nogo),
        "load": start.load,
        "block": str(start.block),
        "set_index": str(start.set_index),
        "start_in_set": str(start.start_in_set),
        "digits_shown": digits,
    }


def compare_with_plan(
    rows: list[dict[str, str]],
    plan: list[Start],
    digits: dict[tuple[int, int], str],
    label: str,
) -> list[str]:
    """Porovná řádky CSV s plánem start po startu; vrátí problémy s popisem label."""
    problems = []
    for row, start in zip(rows, plan, strict=False):
        expected = expected_row_values(start, digits[(start.block, start.set_index)])
        actual: dict[str, object] = {key: row[key] for key in expected}
        actual["foreperiod_s"] = parse_float(row["foreperiod_s"])
        differs = [key for key in expected if actual[key] != expected[key]]
        if differs:
            problems.append(
                f"řádek {row['trial_index']}: nesedí s {label} ({', '.join(differs)})"
            )
    return problems


def check_practice(meta: dict[str, object], rows: list[dict[str, str]]) -> list[str]:
    """Testovací kola: přegeneruje je ze seedu a porovná; musí být před ostrou částí."""
    if not rows:
        return []
    round_length = len(build_practice(0, 1)[0][0])
    rounds = -(
        -len(rows) // round_length
    )  # zaokrouhlení nahoru (poslední může být neúplné)
    practice = build_practice(int(meta["seed"]), rounds)
    starts = [start for round_starts, _ in practice for start in round_starts]
    problems = []
    if len(starts) != len(rows) and meta.get("aborted") is False:
        problems.append("dokončené sezení má neúplné testovací kolo")
    position = 0
    for round_starts, round_digits in practice:
        chunk = rows[position : position + len(round_starts)]
        problems += compare_with_plan(
            chunk, round_starts, round_digits, "testovacím kolem"
        )
        position += len(round_starts)
    if len(starts) < len(rows):
        problems.append("víc řádků testovacího kola, než odpovídá celým kolům")
    return problems


def check_plan(meta: dict[str, object], rows: list[dict[str, str]]) -> list[str]:
    """Přegeneruje plán ze seedu, pořadí bloků a zkrácení v meta a porovná ho s CSV.

    Pozná rozjetí dat a plánu (jiné prodlevy, no-go, zátěž, sady i číslice) a zkrácený
    plán u ostrého sezení.
    """
    if (
        not isinstance(meta.get("seed"), int)
        or meta.get("block_order") not in BLOCK_ORDERS
    ):
        return ["meta: chybí seed nebo platné pořadí bloků, plán nejde přegenerovat"]
    short = bool(meta.get("short"))
    plan, digits = build_session(str(meta["block_order"]), int(meta["seed"]), short)
    is_practice = [row["block"] == str(PRACTICE_BLOCK) for row in rows]
    practice_rows = [
        row for row, practice in zip(rows, is_practice, strict=True) if practice
    ]
    problems = check_practice(meta, practice_rows)
    if is_practice != sorted(is_practice, reverse=True):
        problems.append("testovací kolo není celé před ostrou částí")
    rows = [
        row for row, practice in zip(rows, is_practice, strict=True) if not practice
    ]
    if rows and not practice_rows:
        problems.append("ostrá část bez testovacího kola")
    if meta.get("planned_starts") != len(plan):
        problems.append(
            f"meta: planned_starts {meta.get('planned_starts')} ≠ plán {len(plan)}"
        )
    nick = str(meta.get("participant", ""))
    if short and not short_plan_allowed(bool(meta.get("simulated")), nick):
        problems.append("zkrácený plán (--short) u ostrého nebo pilotního sezení")
    problems += compare_with_plan(rows, plan, digits, "plánem ze seedu")
    return problems


def check_sets(rows: list[dict[str, str]]) -> list[str]:
    """Sady ostré části bez ohledu na seed: 3 řádky, start_in_set 1–3, jedna zátěž."""
    problems = []
    main_rows = [row for row in rows if row["block"] != str(PRACTICE_BLOCK)]
    for key, group in itertools.groupby(
        main_rows, key=lambda r: (r["block"], r["set_index"])
    ):
        group = list(group)
        positions = [row["start_in_set"] for row in group]
        expected = [str(i) for i in range(1, STARTS_PER_SET + 1)]
        if positions != expected:
            problems.append(f"sada {key}: start_in_set {positions}, čekáno {expected}")
        if len({row["load"] for row in group}) != 1:
            problems.append(f"sada {key}: víc zátěží v jedné sadě")
    return problems


def check_digits(rows: list[dict[str, str]], simulated: bool) -> list[str]:
    """Ověří sloupce s číslicemi: počet podle zátěže, odpověď, recall_correct, shodu v sadě.

    U simulace navíc, že odpověď je přesně ta, kterou simulace napsala.
    """
    problems = []
    sets: list[tuple[str, str]] = []  # (číslice, odpověď) sad v pořadí, jak proběhly
    previous_key = None
    for row in rows:
        index = row["trial_index"]
        shown, typed, correct = (
            row["digits_shown"],
            row["digits_typed"],
            row["recall_correct"],
        )
        n_digits = DIGITS_PER_LOAD.get(row["load"], 0)
        key = (row["block"], row["set_index"])
        if key != previous_key:
            sets.append((shown, typed))
        elif sets[-1] != (shown, typed):
            problems.append(f"řádek {index}: jiné číslice než zbytek sady {key}")
        previous_key = key
        if n_digits == 0:
            if (shown, typed, correct) != ("", "", ""):
                problems.append(
                    f"řádek {index}: zátěž bez číslic má mít prázdné sloupce"
                )
            continue
        unique_digits = shown.isdigit() and len(set(shown)) == len(shown)
        if len(shown) != n_digits or not unique_digits:
            problems.append(f"řádek {index}: digits_shown {shown!r} nesedí k zátěži")
        if typed and (not typed.isdigit() or len(typed) > n_digits):
            problems.append(
                f"řádek {index}: digits_typed {typed!r} není platná odpověď"
            )
        if correct != str(typed == shown):
            problems.append(
                f"řádek {index}: recall_correct {correct!r} nesedí s odpovědí"
            )
    if simulated:
        with_digits = [value for value in sets if value[0]]
        for set_number, (shown, typed) in enumerate(with_digits, start=1):
            expected = sim_recall_answer(shown, set_number)
            if typed != expected:
                problems.append(
                    f"sada {set_number}: simulace napsala {expected!r}, uloženo {typed!r}"
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
    """Krátké shrnutí sezení pro výpis (počty a RT jen z ostré části)."""
    n_practice = sum(row["block"] == str(PRACTICE_BLOCK) for row in rows)
    rows = [row for row in rows if row["block"] != str(PRACTICE_BLOCK)]
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
        f"testovací kola: {meta.get('practice_rounds')} ({n_practice} startů), "
        f"ostrých startů: {len(rows)} z {meta.get('planned_starts')}, "
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
    problems.extend(check_digits(rows, bool(meta.get("simulated"))))
    problems.extend(check_plan(meta, rows))
    problems.extend(check_sets(rows))
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
