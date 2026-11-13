"""Testy kontroly dat (check_data.py) na uměle vytvořeném sezení."""

import csv
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

from check_data import check_row, check_rt, check_session
from config import CSV_COLUMNS, LOG_SUFFIX, META_SUFFIX, SIM_DIR_NAME
from logic import (
    companion_path,
    finish_meta,
    make_meta,
    make_plan,
    make_row,
    write_meta,
)

SAMPLE_TIME = datetime(2026, 11, 13, 9, 5, tzinfo=timezone(timedelta(hours=1)))
SAMPLE_RT = {"go": 0.25, "anticipation": 0.05, "commission": 0.3}


def write_session(tmp_path: Path, aborted: bool = False) -> Path:
    """Zapíše platné sezení podle plánu (go starty se stiskem, no-go bez stisku)."""
    tmp_path.mkdir(parents=True, exist_ok=True)
    csv_path = tmp_path / "test_mac_2026-11-13_0905.csv"
    plan = make_plan()
    with csv_path.open("w", newline="", encoding="utf-8") as data_file:
        writer = csv.DictWriter(data_file, fieldnames=CSV_COLUMNS)
        writer.writeheader()
        for trial_index, start in enumerate(plan, start=1):
            outcome = "inhibit" if start.is_nogo else "go"
            writer.writerow(
                make_row(
                    participant="test",
                    machine="mac",
                    start=start,
                    trial_index=trial_index,
                    outcome=outcome,
                    rt=SAMPLE_RT.get(outcome),
                    dropped_frames=0,
                    written_at=SAMPLE_TIME,
                )
            )
    meta = make_meta(
        participant="test",
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
        simulated=False,
    )
    if not aborted:
        meta = finish_meta(meta, SAMPLE_TIME + timedelta(minutes=5), 1)
    write_meta(companion_path(csv_path, META_SUFFIX), meta)
    companion_path(csv_path, LOG_SUFFIX).write_text("", encoding="utf-8")
    return csv_path


META = {"participant": "test", "machine": "mac"}


def valid_row() -> dict[str, str]:
    """Jeden platný řádek CSV tak, jak ho vrátí csv.DictReader (vše jako text)."""
    return {
        "participant": "test",
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
    }
    write_meta(meta_path, meta | sim_meta | changes)
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
    """Escape ve startu 4: přerušené sezení se 3 řádky projde, dokončené ne."""
    csv_path = write_session(tmp_path / SIM_DIR_NAME, aborted=True)
    lines = csv_path.read_text(encoding="utf-8").splitlines()
    csv_path.write_text("\n".join(lines[:4]) + "\n", encoding="utf-8")
    scenario = make_simulated(csv_path)
    with_escape = [*scenario[:3], "escape", *scenario[3:]]
    make_simulated(
        csv_path,
        sim_scenario=with_escape[: len(scenario)],
        planned_starts=len(scenario),
    )
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
    write_meta(
        meta_path, meta | {"keyboard_backend": "event", "window_mode": "windowed"}
    )
    problems = check_session(csv_path)[1]
    assert any("klávesnici iohub" in p for p in problems)
    assert any("režim okna" in p for p in problems)
