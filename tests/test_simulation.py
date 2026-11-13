"""Testy simulace: falešná klávesnice a scénář odpovědí (bez okna PsychoPy)."""

from pathlib import Path

import pytest

from config import (
    FLAG_HEIGHT,
    FLAG_POS,
    GO_OUTCOMES,
    LIGHT_INTERVAL,
    N_LAMPS,
    NOGO_OUTCOMES,
    RESPONSE_WINDOW,
    REST_INTERVAL,
    SIM_DIR_NAME,
    SIM_ESCAPE_AT,
)
from logic import (
    SimulatedKeyboard,
    Start,
    classify_press,
    expected_outcome,
    make_plan,
    make_sim_scenario,
    outcome_without_press,
    parse_args,
    session_data_dir,
    sim_window_size,
)

RATE = 60.0
KEYS = ["space", "escape"]


def frames(seconds: float) -> int:
    """Převod sekund na snímky stejně jako frames() v main.py."""
    return round(seconds * RATE)


def drive_start(kb: SimulatedKeyboard, start: Start) -> str:
    """Volá klávesnici ve stejném pořadí jako run_start v main.py a vrátí výsledek.

    Známé omezení: pořadí je tu opsané z run_start. Když se run_start změní, tyto testy to
    nepoznají; skutečný run_start ověřuje `uv run main.py --sim` + `check_data.py`.
    """
    kb.clearEvents()
    waiting = (N_LAMPS - 1) * frames(LIGHT_INTERVAL) + frames(start.foreperiod)
    for _ in range(waiting):
        if kb.getKeys(keyList=KEYS):
            return "jump_start"
    for i in range(frames(RESPONSE_WINDOW)):
        if i == 0:
            kb.clock.reset()  # v main.py přes win.callOnFlip při prvním flipu
        keys = kb.getKeys(keyList=KEYS)
        if keys:
            return classify_press(keys[0].rt, start.is_nogo)
    return outcome_without_press(start.is_nogo)


def drive_pause(kb: SimulatedKeyboard) -> None:
    """Pauza mezi starty čte jen Escape, stejně jako show_pause v main.py."""
    for _ in range(frames(REST_INTERVAL)):
        assert kb.getKeys(keyList=["escape"]) == []


def make_start(is_nogo: bool) -> Start:
    """Start s prostřední prodlevou."""
    return Start(
        foreperiod=1.25,
        is_nogo=is_nogo,
        load="none",
        block=0,
        set_index=0,
        start_in_set=0,
    )


@pytest.mark.parametrize(
    ("response", "is_nogo", "outcome"),
    [
        ("normal", False, "go"),
        ("fast", False, "anticipation"),
        ("none", False, "omission"),
        ("early", False, "jump_start"),
        ("late_early", False, "jump_start"),
        ("none", True, "inhibit"),
        ("normal", True, "commission"),
        ("fast", True, "commission"),
        ("late_early", True, "jump_start"),
        ("early", True, "jump_start"),
    ],
)
def test_single_response(response: str, is_nogo: bool, outcome: str) -> None:
    """Každý typ odpovědi dá přes protokol run_start očekávaný výsledek."""
    kb = SimulatedKeyboard([response], RATE)
    assert drive_start(kb, make_start(is_nogo)) == outcome
    assert expected_outcome(response, is_nogo) == outcome


def test_reaction_time_is_from_scenario() -> None:
    """Reakční čas stisku je čas ze scénáře, ne zaokrouhlený na snímky."""
    kb = SimulatedKeyboard(["normal"], RATE)
    kb.clearEvents()
    kb.clock.reset()
    presses = [kb.getKeys(keyList=KEYS) for _ in range(frames(RESPONSE_WINDOW))]
    pressed = [keys for keys in presses if keys]
    assert len(pressed) == 1
    assert pressed[0][0].rt == 0.25


def test_whole_plan_matches_expected_outcomes() -> None:
    """Celý plán se scénářem dá výsledky podle expected_outcome a všech 6 typů."""
    plan = make_plan()
    scenario = make_sim_scenario(plan)
    kb = SimulatedKeyboard(scenario, RATE)
    outcomes = []
    for start, response in zip(plan, scenario, strict=True):
        outcome = drive_start(kb, start)
        assert outcome == expected_outcome(response, start.is_nogo)
        outcomes.append(outcome)
        drive_pause(kb)
    assert set(outcomes) == set(GO_OUTCOMES) | set(NOGO_OUTCOMES)


def test_scenario_exhausted() -> None:
    """Po vyčerpání scénáře klávesnice už nic nestiskne."""
    kb = SimulatedKeyboard([], RATE)
    assert drive_start(kb, make_start(False)) == "omission"


def test_session_data_dir() -> None:
    """Simulace ukládá do podsložky sim/, ostatní přímo do data/."""
    assert session_data_dir(Path("data"), simulated=True) == Path("data") / SIM_DIR_NAME
    assert session_data_dir(Path("data"), simulated=False) == Path("data")


def test_escape_in_scenario() -> None:
    """Odpověď "escape" vrátí Escape hned v prvním čtení startu."""
    plan = make_plan()
    scenario = make_sim_scenario(plan, escape_at=SIM_ESCAPE_AT)
    assert scenario[SIM_ESCAPE_AT - 1] == "escape"
    assert scenario.count("escape") == 1
    kb = SimulatedKeyboard(["escape"], RATE)
    kb.clearEvents()
    assert [key.name for key in kb.getKeys(keyList=KEYS)] == ["escape"]


@pytest.mark.parametrize(
    ("args", "expected"),
    [
        ([], (False, None)),
        (["--sim"], (True, None)),
        (["--sim-escape"], (True, SIM_ESCAPE_AT)),
        (["--sim", "--sim-escape"], (True, SIM_ESCAPE_AT)),
    ],
)
def test_parse_args(args: list[str], expected: tuple[bool, int | None]) -> None:
    """Bez argumentů ostrý běh, --sim simulace, --sim-escape simulace s přerušením."""
    assert parse_args(args) == expected


def test_parse_args_rejects_typo() -> None:
    """Překlep v přepínači nesmí tiše spustit ostrý běh."""
    with pytest.raises(ValueError, match="--simm"):
        parse_args(["--simm"])


@pytest.mark.parametrize(
    ("screen", "ratio"), [((1512, 982), 2.0), ((1920, 1080), 1.0), ((1280, 720), 1.0)]
)
def test_sim_window_fits_stimuli(screen: tuple[int, int], ratio: float) -> None:
    """Okno simulace se vejde na displej a vejdou se do něj lampy i vlajka (v pixelech)."""
    width, height = sim_window_size(screen, ratio)
    assert width <= screen[0]
    assert height <= screen[1]
    flag_top = FLAG_POS[1] + FLAG_HEIGHT / 2
    assert height * ratio / 2 >= min(flag_top, screen[1] * ratio / 2)


def test_sim_window_on_retina_is_not_oversized() -> None:
    """Na Retině stačí podíl displeje, okno se zbytečně nezvětší (body ≠ pixely)."""
    assert sim_window_size((1512, 982), 2.0) == (605, 393)
