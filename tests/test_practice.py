"""Testy testovacího kola a simulace s ním (bez okna PsychoPy)."""

from config import (
    DIGITS_PER_LOAD,
    FOREPERIODS,
    PRACTICE_BLOCK,
    PRACTICE_LOAD,
    PRACTICE_SET_NOGO,
    PRACTICE_SINGLE_NOGO,
    SIM_ESCAPE_AT,
    SIM_PRACTICE_ROUNDS,
    STARTS_PER_SET,
)
from logic import (
    build_practice,
    build_session,
    group_sets,
    recall_feedback_text,
    sim_sequence,
    starts_written_before,
)


def test_practice_round_structure() -> None:
    """Část 1: každá prodleva jednou, 1 no-go, bez číslic; část 2: sada s 2 číslicemi."""
    starts, digits = build_practice(1, 1)[0]
    singles, practice_set = starts[: len(FOREPERIODS)], starts[len(FOREPERIODS) :]
    assert sorted(start.foreperiod for start in singles) == sorted(FOREPERIODS)
    assert sum(start.is_nogo for start in singles) == PRACTICE_SINGLE_NOGO
    assert {start.load for start in singles} == {"none"}
    assert [start.set_index for start in singles] == [1, 2, 3, 4]
    assert len(practice_set) == STARTS_PER_SET
    assert sum(start.is_nogo for start in practice_set) == PRACTICE_SET_NOGO
    assert {start.load for start in practice_set} == {PRACTICE_LOAD}
    assert len({start.foreperiod for start in practice_set}) == STARTS_PER_SET
    assert {start.block for start in starts} == {PRACTICE_BLOCK}
    set_key = (PRACTICE_BLOCK, practice_set[0].set_index)
    assert len(digits[set_key]) == DIGITS_PER_LOAD[PRACTICE_LOAD]
    assert all(digits[(PRACTICE_BLOCK, s.set_index)] == "" for s in singles)


def test_practice_part_one_written_per_start() -> None:
    """Část 1 tvoří samostatné skupiny po jednom startu (zápis po každém startu)."""
    starts, _ = build_practice(1, 1)[0]
    sizes = [len(group) for group in group_sets(starts)]
    assert sizes == [1, 1, 1, 1, STARTS_PER_SET]


def test_practice_rounds_deterministic_and_different() -> None:
    """Stejný seed = stejná kola; opakované kolo je jiné; plán ostré části se nemění."""
    assert build_practice(5, 3) == build_practice(5, 3)
    assert build_practice(5, 3)[:2] == build_practice(5, 2)
    rounds = build_practice(5, 3)
    assert rounds[0] != rounds[1]
    before = build_session("ABBA", 5, short=False)
    build_practice(5, 10)
    assert build_session("ABBA", 5, short=False) == before


def test_recall_feedback_text() -> None:
    """Správně / Správně bylo: 4 7 v obou jazycích."""
    assert recall_feedback_text("47", "47", "cs") == "Správně"
    assert recall_feedback_text("47", "4", "cs") == "Správně bylo: 4 7"
    assert recall_feedback_text("47", "74", "en") == "The correct answer was: 4 7"


def test_sim_sequence() -> None:
    """Simulace: dvě testovací kola, pak ostrá část."""
    starts, practice_digits, main_digits = sim_sequence("ABBA", 3, short=True)
    round_length = len(build_practice(3, 1)[0][0])
    plan, _ = build_session("ABBA", 3, short=True)
    assert len(starts) == SIM_PRACTICE_ROUNDS * round_length + len(plan)
    assert starts[-len(plan) :] == plan
    assert [len(digits) for digits in practice_digits] == [1] * SIM_PRACTICE_ROUNDS
    assert len(main_digits) == len(group_sets(plan))


def test_starts_written_before() -> None:
    """Escape: zapsané jsou jen celé skupiny před ním."""
    starts, _, _ = sim_sequence("ABBA", 3, short=True)
    assert starts_written_before(starts, 1) == 0
    assert starts_written_before(starts, 4) == 3  # část 1 po startu
    assert starts_written_before(starts, 6) == 4  # uprostřed sady testovacího kola
    assert starts_written_before(starts, SIM_ESCAPE_AT) == 2 * 7 + STARTS_PER_SET
