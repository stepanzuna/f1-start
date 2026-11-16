"""Testy kontroly dat (check_data.py) na uměle vytvořeném sezení."""

import csv
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from check_data import check_digits, check_row, check_rt, check_session, check_sets
from config import (
    CSV_COLUMNS,
    LOG_SUFFIX,
    META_SUFFIX,
    SIM_DIR_NAME,
    SIM_ESCAPE_AT,
    SIM_LANGUAGE,
    SIM_MACHINE_ID,
    SIM_NICK,
    SIM_PRACTICE_ROUNDS,
    SIM_PX_PER_CM,
)
from logic import (
    Calibration,
    build_practice,
    build_session,
    companion_path,
    finish_meta,
    make_meta,
    make_row,
    write_json,
)
from simulation import (
    sim_effort,
    sim_recall_answer,
)

SAMPLE_TIME = datetime(2026, 11, 13, 9, 5, tzinfo=timezone(timedelta(hours=1)))
SAMPLE_RT = {"go": 0.25, "anticipation": 0.05, "commission": 0.3}
SAMPLE_SEED = 12345


def write_session(tmp_path: Path, aborted: bool = False) -> Path:
    """Zapíše platné sezení podle plánu (go starty se stiskem, no-go bez stisku).

    Ve složce sim/ jako simulace s nickem „sim“, jinde jako ostré sezení s nickem „anna“.
    """
    tmp_path.mkdir(parents=True, exist_ok=True)
    nick = SIM_NICK if tmp_path.name == SIM_DIR_NAME else "anna"
    csv_path = tmp_path / f"{nick}_mac_2026-11-13_0905.csv"
    simulated = tmp_path.name == SIM_DIR_NAME
    plan, digits = build_session("ABBA", SAMPLE_SEED, short=False)
    rounds = build_practice(SAMPLE_SEED, SIM_PRACTICE_ROUNDS if simulated else 1)
    sequence = [
        (s, ds[(s.block, s.set_index)]) for starts, ds in rounds for s in starts
    ]
    sequence += [(s, digits[(s.block, s.set_index)]) for s in plan]
    with csv_path.open("w", newline="", encoding="utf-8") as data_file:
        writer = csv.DictWriter(data_file, fieldnames=CSV_COLUMNS)
        writer.writeheader()
        set_number = 0
        previous_key = None
        for trial_index, (start, shown) in enumerate(sequence, start=1):
            key = (start.block, start.set_index)
            if key != previous_key and shown:
                set_number += 1
            previous_key = key
            outcome = "inhibit" if start.is_nogo else "go"
            typed = (
                sim_recall_answer(shown, set_number) if simulated and shown else shown
            )
            writer.writerow(
                make_row(
                    participant=nick,
                    machine="mac",
                    start=start,
                    trial_index=trial_index,
                    outcome=outcome,
                    rt=SAMPLE_RT.get(outcome),
                    dropped_frames=0,
                    written_at=SAMPLE_TIME,
                    digits_shown=shown,
                    digits_typed=typed,
                )
            )
    meta = make_meta(
        participant=nick,
        machine="mac",
        started_at=SAMPLE_TIME,
        environment={
            "platform": "macOS",
            "python_version": "3.11",
            "psychopy_version": "2026.2.5",
            "git_commit": "abc1234",
        },
        frame_rate=60.0,
        window_mode="fullscr",
        window_size=(3024, 1964),
        keyboard_backend="iohub",
        planned_starts=len(plan),
        block_order="ABBA",
        language="cs",
        seed=SAMPLE_SEED,
        short=False,
        simulated=False,
        machine_id="a1b2c3d4",
        calibration=Calibration(50.0, (3024, 1964), "2026-11-16T10:00:00+01:00"),
        dpi_aware=None,
    )
    if not aborted:
        meta = finish_meta(meta, SAMPLE_TIME + timedelta(minutes=5), 1, len(rounds))
        ratings = (
            [int(sim_effort(b)) for b in range(1, 5)] if simulated else [5, 4, 6, 5]
        )
        meta = meta | {"effort_ratings": ratings}
    write_json(companion_path(csv_path, META_SUFFIX), meta)
    companion_path(csv_path, LOG_SUFFIX).write_text("", encoding="utf-8")
    return csv_path


META = {"participant": "anna", "machine": "mac"}


def valid_row() -> dict[str, str]:
    """Jeden platný řádek CSV tak, jak ho vrátí csv.DictReader (vše jako text)."""
    return {
        "participant": "anna",
        "machine": "mac",
        "load": "none",
        "timestamp": "2026-11-13T09:05:00+01:00",
        "trial_index": "1",
        "is_nogo": "False",
        "outcome": "go",
        "rt_ms": "250.0",
        "foreperiod_s": "1.25",
        "block": "0",
        "phase": "practice",
        "dropped_frames": "0",
    }


def test_valid_session_has_no_problems(tmp_path: Path) -> None:
    """Platné dokončené sezení projde bez problémů."""
    summary, problems, warnings = check_session(write_session(tmp_path))
    assert problems == []
    assert warnings == []
    assert "aborted=False" in summary


def test_aborted_session_with_partial_rows(tmp_path: Path) -> None:
    """Přerušené sezení nemusí mít všechny řádky."""
    csv_path = write_session(tmp_path, aborted=True)
    lines = csv_path.read_text(encoding="utf-8").splitlines()
    csv_path.write_text("\n".join(lines[:4]) + "\n", encoding="utf-8")
    assert check_session(csv_path)[1] == []


def test_finished_session_with_missing_rows(tmp_path: Path) -> None:
    """Dokončené sezení s chybějícími řádky je chyba."""
    csv_path = write_session(tmp_path)
    lines = csv_path.read_text(encoding="utf-8").splitlines()
    csv_path.write_text("\n".join(lines[:4]) + "\n", encoding="utf-8")
    problems = check_session(csv_path)[1]
    assert any("plán má" in problem for problem in problems)


def test_missing_meta(tmp_path: Path) -> None:
    """Chybějící metadata jsou chyba."""
    csv_path = write_session(tmp_path)
    companion_path(csv_path, META_SUFFIX).unlink()
    assert check_session(csv_path)[1] == [
        f"chybí metadata {csv_path.stem}{META_SUFFIX}"
    ]


def test_valid_row() -> None:
    """Platný řádek nemá problémy."""
    assert check_row(valid_row(), 1, META) == []


def test_row_problems() -> None:
    """Chybný výsledek, prodleva, fáze a pořadí se odhalí."""
    row = valid_row() | {"outcome": "inhibit", "foreperiod_s": "1.0", "phase": "main"}
    problems = check_row(row, 2, META)
    assert len(problems) == 4
    for expected in ("trial_index 1", "outcome 'inhibit'", "foreperiod_s", "phase"):
        assert any(expected in problem for problem in problems), expected


def test_rt_rules() -> None:
    """rt_ms jen u výsledků s reakcí, a v mezích podle výsledku."""
    assert check_rt("go", "250.0") == []
    assert check_rt("omission", "") == []
    assert check_rt("omission", "250.0") != []
    assert check_rt("go", "") != []
    assert check_rt("go", "50.0") != []
    assert check_rt("anticipation", "150.0") != []
    assert check_rt("anticipation", "100.0") == []  # 0,09996 s zaokrouhlené
    assert check_rt("go", "100.0") == []
    assert check_rt("commission", "1600.0") != []


def test_truncated_last_row(tmp_path: Path) -> None:
    """Oříznutý poslední řádek (pád při zápisu) se nahlásí, kontrola nespadne."""
    csv_path = write_session(tmp_path, aborted=True)
    text = csv_path.read_text(encoding="utf-8")
    csv_path.write_text(text[: text.rindex(",")], encoding="utf-8")
    problems = check_session(csv_path)[1]
    assert any("neúplný" in problem for problem in problems)


def test_go_without_rt_does_not_crash(tmp_path: Path) -> None:
    """go s prázdným rt_ms se nahlásí jako problém, shrnutí nespadne."""
    csv_path = write_session(tmp_path)
    text = csv_path.read_text(encoding="utf-8")
    csv_path.write_text(text.replace(",go,250.0,", ",go,,", 1), encoding="utf-8")
    problems = check_session(csv_path)[1]
    assert any("číselné rt_ms" in problem for problem in problems)


def test_missing_log(tmp_path: Path) -> None:
    """Chybějící log je problém."""
    csv_path = write_session(tmp_path)
    companion_path(csv_path, LOG_SUFFIX).unlink()
    assert any("chybí log" in problem for problem in check_session(csv_path)[1])


def test_dropped_frames_are_warnings(tmp_path: Path) -> None:
    """Vypadlé snímky ve startu jsou varování, ne problém."""
    csv_path = write_session(tmp_path)
    lines = csv_path.read_text(encoding="utf-8").splitlines()
    first = lines[1].split(",")
    first[CSV_COLUMNS.index("dropped_frames")] = "1"
    lines[1] = ",".join(first)
    csv_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    _, problems, warnings = check_session(csv_path)
    assert problems == []
    assert warnings == ["start 1: 1 vypadlých snímků"]


def make_simulated(csv_path: Path, **changes: object) -> list[str]:
    """Přepíše meta na simulaci se scénářem, který odpovídá zapsaným řádkům (go/inhibit)."""
    meta_path = companion_path(csv_path, META_SUFFIX)
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    with csv_path.open(newline="", encoding="utf-8") as data_file:
        rows = list(csv.DictReader(data_file))
    scenario = ["none" if row["is_nogo"] == "True" else "normal" for row in rows]
    sim_meta = {
        "simulated": True,
        "sim_scenario": scenario,
        "keyboard_backend": "simulated",
        "language": SIM_LANGUAGE,
        "machine_id": SIM_MACHINE_ID,
        "px_per_cm": SIM_PX_PER_CM,
        "calibrated_at": None,
    }
    write_json(meta_path, meta | sim_meta | changes)
    return scenario


def test_simulation_matching_scenario(tmp_path: Path) -> None:
    """Simulace, jejíž výsledky odpovídají scénáři, projde."""
    csv_path = write_session(tmp_path / SIM_DIR_NAME)
    make_simulated(csv_path)
    assert check_session(csv_path)[1] == []


def test_simulation_wrong_outcome(tmp_path: Path) -> None:
    """Výsledek, který nesedí se scénářem, je problém (chyba ve vyhodnocení startu)."""
    csv_path = write_session(tmp_path / SIM_DIR_NAME)
    make_simulated(csv_path)
    text = csv_path.read_text(encoding="utf-8")
    csv_path.write_text(text.replace(",go,250.0,", ",go,180.0,", 1), encoding="utf-8")
    problems = check_session(csv_path)[1]
    assert any("simulace čekala rt_ms 250.0" in problem for problem in problems)


def test_simulation_wrong_outcome_branch(tmp_path: Path) -> None:
    """Jiný výsledek, než předpověděl scénář, je problém (chyba ve vyhodnocení startu)."""
    csv_path = write_session(tmp_path / SIM_DIR_NAME)
    scenario = make_simulated(csv_path)
    go_index = scenario.index("normal")
    make_simulated(
        csv_path, sim_scenario=[*scenario[:go_index], "fast", *scenario[go_index + 1 :]]
    )
    problems = check_session(csv_path)[1]
    assert any("čekala anticipation, program vyhodnotil go" in p for p in problems)


def test_simulation_without_scenario(tmp_path: Path) -> None:
    """Simulace bez scénáře nebo s neznámou odpovědí je problém, ne pád."""
    csv_path = write_session(tmp_path / SIM_DIR_NAME)
    scenario = make_simulated(csv_path, sim_scenario=None)
    assert any("nemá scénář" in p for p in check_session(csv_path)[1])
    make_simulated(csv_path, sim_scenario=["nesmysl", *scenario[1:]])
    assert any("neznámé odpovědi" in p for p in check_session(csv_path)[1])


def test_simulation_with_escape(tmp_path: Path) -> None:
    """Escape ve startu 4 (část 1 testovacího kola, zápis po startu): 3 řádky."""
    csv_path = write_session(tmp_path / SIM_DIR_NAME, aborted=True)
    lines = csv_path.read_text(encoding="utf-8").splitlines()
    scenario = make_simulated(csv_path)
    csv_path.write_text("\n".join(lines[:4]) + "\n", encoding="utf-8")
    make_simulated(csv_path, sim_scenario=[*scenario[:3], "escape", *scenario[4:]])
    assert check_session(csv_path)[1] == []
    make_simulated(csv_path, sim_scenario=["escape", *scenario[1:]])
    assert any("s Escapem ve startu 1" in p for p in check_session(csv_path)[1])


def test_simulation_outside_sim_dir(tmp_path: Path) -> None:
    """Simulace mimo data/sim/ i ostrá data v data/sim/ jsou problém."""
    csv_path = write_session(tmp_path)
    make_simulated(csv_path)
    assert any("simulace patří do" in p for p in check_session(csv_path)[1])
    real_in_sim = write_session(tmp_path / SIM_DIR_NAME)
    assert any("simulace patří do" in p for p in check_session(real_in_sim)[1])


def test_real_session_needs_iohub_and_full_screen(tmp_path: Path) -> None:
    """Ostré sezení se simulovanou klávesnicí nebo menším oknem neprojde."""
    csv_path = write_session(tmp_path)
    meta_path = companion_path(csv_path, META_SUFFIX)
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    write_json(
        meta_path, meta | {"keyboard_backend": "event", "window_mode": "windowed"}
    )
    problems = check_session(csv_path)[1]
    assert any("klávesnici iohub" in p for p in problems)
    assert any("režim okna" in p for p in problems)


def test_test_nick_belongs_to_test_dir(tmp_path: Path) -> None:
    """Sezení s nickem test… přímo v data/ je problém (patří do data/test/)."""
    csv_path = write_session(tmp_path)
    meta_path = companion_path(csv_path, META_SUFFIX)
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    write_json(meta_path, meta | {"participant": "test2"})
    assert any("patří do test/" in p for p in check_session(csv_path)[1])


def test_invalid_language_and_block_order(tmp_path: Path) -> None:
    """Neznámý jazyk nebo pořadí bloků v meta je problém."""
    csv_path = write_session(tmp_path)
    meta_path = companion_path(csv_path, META_SUFFIX)
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    write_json(meta_path, meta | {"language": "de", "block_order": "AABB"})
    problems = check_session(csv_path)[1]
    assert any("jazyk 'de'" in p for p in problems)
    assert any("pořadí bloků 'AABB'" in p for p in problems)


def digit_row(
    index: int, load: str, set_index: int, shown: str, typed: str
) -> dict[str, str]:
    """Řádek CSV (jako text) jen se sloupci, které čte check_digits."""
    correct = str(typed == shown) if shown else ""
    return {
        "trial_index": str(index),
        "load": load,
        "block": "1",
        "set_index": str(set_index),
        "digits_shown": shown,
        "digits_typed": typed if shown else "",
        "recall_correct": correct,
    }


def test_check_digits_valid_and_invalid() -> None:
    """Platné sady projdou; špatný počet, opakování, nesoulad v sadě a recall_correct ne."""
    good = [digit_row(i, "low", 1, "47", "47") for i in (1, 2, 3)]
    good += [digit_row(i, "high", 2, "093182", "093") for i in (4, 5, 6)]
    good += [digit_row(7, "none", 3, "", "")]
    assert check_digits(good, simulated=False) == []
    bad = [
        digit_row(1, "low", 1, "477", "47"),  # 3 číslice při nízké zátěži
        digit_row(2, "high", 2, "093189", "0"),  # 9 dvakrát
        digit_row(3, "high", 2, "093182", "0"),  # jiné než zbytek sady 2
        digit_row(4, "low", 4, "47", "47") | {"recall_correct": "False"},
    ]
    problems = check_digits(bad, simulated=False)
    for expected in (
        "řádek 1: digits_shown",
        "řádek 2: digits_shown",
        "řádek 3: jiné",
        "řádek 4",
    ):
        assert any(problem.startswith(expected) for problem in problems), expected


def test_check_digits_simulation() -> None:
    """U simulace musí odpověď odpovídat vzoru: sada 1 správně, sada 2 špatná poslední číslice."""
    rows = [digit_row(1, "low", 1, "47", "47"), digit_row(2, "low", 2, "47", "40")]
    assert check_digits(rows, simulated=True) == []
    rows[1] = digit_row(2, "low", 2, "47", "47")
    assert any("sada 2" in problem for problem in check_digits(rows, simulated=True))


@pytest.mark.parametrize(
    ("escape_at", "written"),
    [
        (6, 4),
        (SIM_ESCAPE_AT, 2 * 7 + 3),
    ],  # uprostřed sady testovacího kola / 2. ostré sady
)
def test_simulation_with_escape_mid_set(
    tmp_path: Path, escape_at: int, written: int
) -> None:
    """Escape uprostřed sady: rozdělaná sada se nezapíše, dřívější řádky ano."""
    csv_path = write_session(tmp_path / SIM_DIR_NAME, aborted=True)
    lines = csv_path.read_text(encoding="utf-8").splitlines()
    scenario = make_simulated(csv_path)
    with_escape = [*scenario[: escape_at - 1], "escape", *scenario[escape_at:]]
    for n_rows, ok in ((written, True), (written + 1, False)):
        csv_path.write_text("\n".join(lines[: n_rows + 1]) + "\n", encoding="utf-8")
        make_simulated(csv_path, sim_scenario=with_escape)
        problems = check_session(csv_path)[1]
        assert (problems == []) is ok, problems


def test_plan_mismatch_detected(tmp_path: Path) -> None:
    """Řádek, který nesedí s plánem přegenerovaným ze seedu, je problém."""
    csv_path = write_session(tmp_path)
    lines = csv_path.read_text(encoding="utf-8").splitlines()
    cells = lines[1].split(",")
    nogo = CSV_COLUMNS.index("is_nogo")
    outcome = CSV_COLUMNS.index("outcome")
    rt_ms = CSV_COLUMNS.index("rt_ms")
    flipped = "False" if cells[nogo] == "True" else "True"
    cells[nogo], cells[outcome], cells[rt_ms] = flipped, "omission", ""
    if flipped == "True":
        cells[outcome] = "inhibit"
    lines[1] = ",".join(cells)
    csv_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    problems = check_session(csv_path)[1]
    assert any("řádek 1: nesedí s testovacím kolem (is_nogo)" in p for p in problems)


def test_short_plan_only_for_tests_and_simulation(tmp_path: Path) -> None:
    """Zkrácený plán (meta short=True) u ostrého sezení je problém."""
    csv_path = write_session(tmp_path)
    meta_path = companion_path(csv_path, META_SUFFIX)
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    write_json(meta_path, meta | {"short": True})
    assert any("zkrácený plán" in p for p in check_session(csv_path)[1])


def test_check_sets() -> None:
    """Sada musí mít start_in_set 1–3 a jednu zátěž; testovací kolo (blok 0) se nekontroluje."""

    def row(block: str, set_index: str, position: str, load: str) -> dict[str, str]:
        return {
            "block": block,
            "set_index": set_index,
            "start_in_set": position,
            "load": load,
        }

    good = [row("1", "1", str(i), "low") for i in (1, 2, 3)] + [
        row("0", "0", "0", "none")
    ]
    assert check_sets(good) == []
    bad = [row("1", "1", "1", "low"), row("1", "1", "2", "high")]
    problems = check_sets(bad)
    assert any("start_in_set" in p for p in problems)
    assert any("víc zátěží" in p for p in problems)


def test_practice_must_come_first(tmp_path: Path) -> None:
    """Ostrá část bez testovacího kola nebo s kolem uprostřed je problém."""
    csv_path = write_session(tmp_path)
    lines = csv_path.read_text(encoding="utf-8").splitlines()
    header, practice, main_rows = lines[0], lines[1:8], lines[8:]
    csv_path.write_text("\n".join([header, *main_rows]) + "\n", encoding="utf-8")
    assert any("bez testovacího kola" in p for p in check_session(csv_path)[1])
    moved = [header, *main_rows[:3], *practice, *main_rows[3:]]
    csv_path.write_text("\n".join(moved) + "\n", encoding="utf-8")
    assert any("není celé před ostrou částí" in p for p in check_session(csv_path)[1])


def test_effort_ratings(tmp_path: Path) -> None:
    """Dokončené sezení: 4 hodnocení 1–9; chybějící nebo mimo rozsah je problém."""
    csv_path = write_session(tmp_path)
    meta_path = companion_path(csv_path, META_SUFFIX)
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    for ratings, expected in (([5, 4, 6], "3 hodnocení"), ([5, 4, 6, 10], "1–9")):
        write_json(meta_path, meta | {"effort_ratings": ratings})
        assert any(expected in p for p in check_session(csv_path)[1]), ratings


def test_effort_ratings_simulation(tmp_path: Path) -> None:
    """U simulace musí hodnocení odpovídat tomu, co simulace napsala."""
    csv_path = write_session(tmp_path / SIM_DIR_NAME)
    make_simulated(csv_path)
    assert check_session(csv_path)[1] == []
    make_simulated(csv_path, effort_ratings=[9, 9, 9, 9])
    assert any("simulace hodnotila" in p for p in check_session(csv_path)[1])


def test_effort_ratings_aborted_match_complete_blocks(tmp_path: Path) -> None:
    """Přerušené sezení: hodnocení jen za bloky, které jsou v CSV celé (nebo o jedno méně)."""
    csv_path = write_session(tmp_path, aborted=True)
    lines = csv_path.read_text(encoding="utf-8").splitlines()
    practice = 7
    one_block = lines[: 1 + practice + 24]  # hlavička, testovací kolo, celý blok 1
    csv_path.write_text("\n".join(one_block) + "\n", encoding="utf-8")
    meta_path = companion_path(csv_path, META_SUFFIX)
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    for ratings, ok in (([], True), ([5], True), ([5, 6], False)):
        write_json(meta_path, meta | {"effort_ratings": ratings})
        problems = check_session(csv_path)[1]
        assert (not any("hodnocení úsilí" in p for p in problems)) is ok, (
            ratings,
            problems,
        )


def rewrite_meta(csv_path: Path, **changes: object) -> None:
    """Přepíše vybrané klíče v meta sezení."""
    meta_path = companion_path(csv_path, META_SUFFIX)
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    write_json(meta_path, meta | changes)


@pytest.mark.parametrize(
    ("changes", "expected"),
    [
        ({"px_per_cm": 500.0}, "meta: px_per_cm 500.0 mimo věrohodný rozsah"),
        ({"px_per_cm": None}, "meta: px_per_cm None mimo věrohodný rozsah"),
        ({"machine_id": "PC-ANNA"}, "meta: identifikátor počítače 'PC-ANNA'"),
        ({"calibrated_at": None}, "ostré sezení nemá platné datum kalibrace"),
        ({"calibrated_at": "včera"}, "ostré sezení nemá platné datum kalibrace"),
        (
            {"machine_id": SIM_MACHINE_ID},
            "ostré sezení má identifikátor počítače simulace",
        ),
    ],
)
def test_calibration_problems(
    tmp_path: Path, changes: dict[str, object], expected: str
) -> None:
    """Nevěrohodná kalibrace, neplatný identifikátor, ostré sezení bez kalibrace."""
    csv_path = write_session(tmp_path)
    rewrite_meta(csv_path, **changes)
    problems = check_session(csv_path)[1]
    assert any(problem.startswith(expected) for problem in problems), problems


def test_missing_calibration_key(tmp_path: Path) -> None:
    """Meta ze starší verze programu (bez kalibrace) neprojde."""
    csv_path = write_session(tmp_path)
    meta_path = companion_path(csv_path, META_SUFFIX)
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    del meta["px_per_cm"]
    write_json(meta_path, meta)
    assert "meta: chybí klíč px_per_cm" in check_session(csv_path)[1]


def test_simulation_needs_fixed_calibration(tmp_path: Path) -> None:
    """Simulace má pevných SIM_PX_PER_CM a identifikátor simulace."""
    csv_path = write_session(tmp_path / SIM_DIR_NAME)
    make_simulated(csv_path, px_per_cm=99.0)
    problems = check_session(csv_path)[1]
    assert any(problem.startswith("simulace má mít px_per_cm") for problem in problems)
    make_simulated(csv_path, calibrated_at="2026-11-16T21:14:00+01:00")
    problems = check_session(csv_path)[1]
    assert any(problem.startswith("simulace má mít px_per_cm") for problem in problems)


@pytest.mark.parametrize(
    ("machine", "dpi_aware", "warned"),
    [
        ("win", True, False),
        ("win", False, True),
        ("win", None, True),
        ("mac", None, False),
    ],
)
def test_windows_without_dpi_awareness_warns(
    tmp_path: Path, machine: str, dpi_aware: bool | None, warned: bool
) -> None:
    """Windows bez DPI awareness je varování (velikost drží kalibrace), ne chyba."""
    csv_path = write_session(tmp_path)
    rewrite_meta(csv_path, dpi_aware=dpi_aware)
    if machine == "win":
        win_path = csv_path.with_name(csv_path.name.replace("_mac_", "_win_"))
        for suffix in ("", META_SUFFIX, LOG_SUFFIX):
            source = csv_path if not suffix else companion_path(csv_path, suffix)
            target = win_path if not suffix else companion_path(win_path, suffix)
            source.rename(target)
        csv_path = win_path
        lines = csv_path.read_text(encoding="utf-8").replace(",mac,", ",win,")
        csv_path.write_text(lines, encoding="utf-8")
        rewrite_meta(csv_path, machine="win")
    _, problems, warnings = check_session(csv_path)
    assert problems == []
    assert any("DPI awareness" in warning for warning in warnings) is warned
