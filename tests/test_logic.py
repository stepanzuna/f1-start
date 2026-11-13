"""Testy čisté logiky experimentu (bez PsychoPy)."""

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from config import CSV_COLUMNS, FOREPERIODS, GO_PER_FOREPERIOD, NOGO_PER_FOREPERIOD
from logic import (
    Start,
    companion_path,
    finish_meta,
    git_commit,
    machine_code,
    make_data_path,
    make_meta,
    make_plan,
    make_row,
    write_meta,
)

PRAGUE_WINTER = timezone(timedelta(hours=1))
SAMPLE_TIME = datetime(2026, 11, 13, 9, 5, 7, tzinfo=PRAGUE_WINTER)
SAMPLE_START = Start(
    foreperiod=1.25, is_nogo=False, load="none", block=0, set_index=0, start_in_set=0
)


def sample_row(rt: float | None) -> dict[str, object]:
    """Vzorový řádek CSV s daným reakčním časem."""
    return make_row(
        participant="test",
        machine="mac",
        start=SAMPLE_START,
        trial_index=3,
        outcome="go" if rt is not None else "omission",
        rt=rt,
        dropped_frames=0,
        written_at=SAMPLE_TIME,
    )


def test_plan_length() -> None:
    """Plán má pro každou prodlevu všechny go i no-go starty."""
    plan = make_plan()
    assert len(plan) == len(FOREPERIODS) * (GO_PER_FOREPERIOD + NOGO_PER_FOREPERIOD)


def test_plan_counts_per_foreperiod() -> None:
    """Každá prodleva má přesně daný počet go a no-go startů."""
    plan = make_plan()
    for foreperiod in FOREPERIODS:
        starts = [start for start in plan if start.foreperiod == foreperiod]
        n_nogo = sum(start.is_nogo for start in starts)
        assert n_nogo == NOGO_PER_FOREPERIOD
        assert len(starts) - n_nogo == GO_PER_FOREPERIOD


def test_machine_code() -> None:
    """Systém se převede na kód stroje, neznámý systém skončí chybou."""
    assert machine_code("darwin") == "mac"
    assert machine_code("win32") == "win"
    with pytest.raises(ValueError):
        machine_code("linux")


def test_data_path() -> None:
    """Název souboru má tvar {nick}_{stroj}_{YYYY-MM-DD_HHMM}.csv."""
    path = make_data_path(Path("data"), "test", "mac", SAMPLE_TIME)
    assert path == Path("data") / "test_mac_2026-11-13_0905.csv"


def test_row_columns() -> None:
    """Řádek má přesně sloupce ze specifikace a ve stejném pořadí."""
    assert list(sample_row(0.2345)) == list(CSV_COLUMNS)


def test_row_values() -> None:
    """Reakční čas v ms na 1 desetinné místo, fáze podle bloku, čas zápisu ISO 8601."""
    row = sample_row(0.23456)
    assert row["rt_ms"] == 234.6
    assert row["phase"] == "practice"
    assert row["timestamp"] == "2026-11-13T09:05:07+01:00"


def test_row_without_rt() -> None:
    """Bez reakce zůstane rt_ms prázdné."""
    assert sample_row(None)["rt_ms"] == ""


def sample_meta() -> dict[str, object]:
    """Vzorová metadata na začátku sezení."""
    return make_meta(
        participant="test",
        machine="mac",
        started_at=SAMPLE_TIME,
        environment={"platform": "macOS-27.0-arm64", "psychopy_version": "2026.2.5"},
        frame_rate=60.0123456,
        window_mode="fullscr",
        window_size=(3024, 1964),
        keyboard_backend="iohub",
        planned_starts=16,
        simulated=False,
    )


def test_companion_path() -> None:
    """Meta a log mají stejný základ názvu jako CSV."""
    csv_path = Path("data") / "test_mac_2026-11-13_0905.csv"
    assert (
        companion_path(csv_path, "_meta.json").name
        == "test_mac_2026-11-13_0905_meta.json"
    )
    assert (
        companion_path(csv_path, "_log.txt").name == "test_mac_2026-11-13_0905_log.txt"
    )


def test_meta_starts_aborted() -> None:
    """Nová metadata jsou označená jako přerušená, dokud sezení řádně neskončí."""
    meta = sample_meta()
    assert meta["aborted"] is True
    assert meta["ended_at"] is None
    assert meta["platform"] == "macOS-27.0-arm64"
    assert meta["frame_rate_hz"] == 60.012
    assert meta["window_size_px"] == [3024, 1964]
    assert meta["timing_s"]["FOREPERIODS"] == list(FOREPERIODS)


def test_finish_meta() -> None:
    """Dokončení sezení zruší příznak přerušení a nezmění původní slovník."""
    meta = sample_meta()
    finished = finish_meta(meta, SAMPLE_TIME + timedelta(minutes=15), 2)
    assert finished["aborted"] is False
    assert finished["ended_at"] == "2026-11-13T09:20:07+01:00"
    assert finished["dropped_frames_total"] == 2
    assert meta["aborted"] is True


def test_write_meta_roundtrip(tmp_path: Path) -> None:
    """Uložená metadata jdou načíst zpět a nezůstane po nich dočasný soubor."""
    path = tmp_path / "x_meta.json"
    write_meta(path, sample_meta())
    write_meta(path, finish_meta(sample_meta(), SAMPLE_TIME, 0))
    assert json.loads(path.read_text(encoding="utf-8"))["aborted"] is False
    assert [p.name for p in tmp_path.iterdir()] == ["x_meta.json"]


def test_git_commit_outside_repo(tmp_path: Path) -> None:
    """Mimo git repozitář vrátí "unknown" místo pádu."""
    assert git_commit(tmp_path) == "unknown"


def test_git_commit_in_repo() -> None:
    """V repozitáři projektu vrátí krátký hash, případně s příponou -dirty."""
    commit = git_commit(Path(__file__).parent.parent)
    assert commit != "unknown"
    assert len(commit.removesuffix("-dirty")) >= 7


def test_row_phase_main() -> None:
    """Ostré bloky (block 1–4) mají phase "main"."""
    start = Start(
        foreperiod=0.5, is_nogo=True, load="high", block=2, set_index=1, start_in_set=3
    )
    row = make_row(
        participant="test",
        machine="win",
        start=start,
        trial_index=1,
        outcome="inhibit",
        rt=None,
        dropped_frames=0,
        written_at=SAMPLE_TIME,
    )
    assert row["phase"] == "main"


def test_meta_with_numpy_values_is_json(tmp_path: Path) -> None:
    """Hodnoty z PsychoPy (numpy) převedené jako v main.py jdou uložit do JSON."""
    import numpy as np

    size = np.array([3024, 1964])
    meta = make_meta(
        participant="test",
        machine="mac",
        started_at=SAMPLE_TIME,
        environment={},
        frame_rate=float(np.float64(59.98)),
        window_mode="fullscr",
        window_size=(int(size[0]), int(size[1])),
        keyboard_backend="iohub",
        planned_starts=16,
        simulated=False,
    )
    write_meta(tmp_path / "m.json", meta)
    assert (
        json.loads((tmp_path / "m.json").read_text(encoding="utf-8"))["frame_rate_hz"]
        == 59.98
    )
