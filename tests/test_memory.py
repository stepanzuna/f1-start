"""Testy paměťové zátěže: sady, číslice, vybavení a simulace vybavení (bez okna PsychoPy)."""

import random
from datetime import datetime, timedelta, timezone

import pytest

from config import (
    DIGITS_PER_LOAD,
    SIM_INTRO_KEYS,
    SIM_RECALL_CYCLE,
    STARTS_PER_SET,
)
from logic import (
    build_session,
    edit_recall,
    group_sets,
    make_digits,
    make_row,
    make_set_digits,
)
from simulation import (
    make_sim_typed_keys,
    sim_recall_answer,
    sim_recall_keys,
)


def sample_plan() -> list:
    """Plný plán sezení s pořadím ABBA ze seedu 1."""
    return build_session("ABBA", 1, short=False)[0]


SAMPLE_TIME = datetime(2026, 11, 13, 9, 5, tzinfo=timezone(timedelta(hours=1)))


def test_group_sets() -> None:
    """Skupiny odpovídají sadám po STARTS_PER_SET startech."""
    plan = sample_plan()
    groups = group_sets(plan)
    assert sum(len(group) for group in groups) == len(plan)
    assert all(len(group) == STARTS_PER_SET for group in groups)
    for group in groups:
        assert len({start.set_index for start in group}) == 1


@pytest.mark.parametrize("load", ["low", "high"])
def test_make_digits(load: str) -> None:
    """Počet číslic podle zátěže, bez opakování, jen 0–9."""
    rng = random.Random(1)
    for _ in range(200):
        digits = make_digits(load, rng)
        assert len(digits) == DIGITS_PER_LOAD[load]
        assert len(set(digits)) == len(digits)
        assert digits.isdigit()


def test_make_digits_zero_can_be_first_and_seed_repeats() -> None:
    """Nula smí být první; stejný seed dá stejné číslice."""
    rng = random.Random(7)
    firsts = {make_digits("high", rng)[0] for _ in range(300)}
    assert "0" in firsts
    assert make_digits("high", random.Random(3)) == make_digits(
        "high", random.Random(3)
    )
    assert make_digits("none", random.Random(3)) == ""


def test_make_set_digits() -> None:
    """Každá sada má své číslice podle své zátěže."""
    plan = sample_plan()
    digits = make_set_digits(plan, random.Random(1))
    assert len(digits) == len(group_sets(plan))
    for start in plan:
        assert (
            len(digits[(start.block, start.set_index)]) == DIGITS_PER_LOAD[start.load]
        )


@pytest.mark.parametrize(
    ("text", "name", "char", "expected"),
    [
        ("4", "7", "7", "47"),
        ("4", "ý", "ý", "47"),  # česká horní řada bez Shiftu = 7
        ("4", "num_7", "7", "47"),  # numerická klávesnice
        ("4", "num_add", "+", "41"),  # česká horní řada: + = 1 (iohub: num_add)
        ("4", "ý", "Ý", "47"),  # Caps Lock na české klávesnici
        ("4", "a", "a", "4"),
        ("47", "1", "1", "47"),  # víc číslic, než bylo zobrazeno
        ("47", "backspace", "", "4"),
    ],
)
def test_edit_recall(text: str, name: str, char: str, expected: str) -> None:
    """Vybavení přijme jen číslice (i z české horní řady), nejvýš tolik, kolik bylo."""
    assert edit_recall(text, name, char, 2) == expected


def make_sample_row(shown: str, typed: str) -> dict[str, object]:
    """Řádek CSV pro start v sadě s danými číslicemi."""
    start = sample_plan()[0]
    return make_row(
        participant="anna",
        machine="mac",
        start=start,
        trial_index=1,
        outcome="go",
        rt=0.25,
        dropped_frames=0,
        written_at=SAMPLE_TIME,
        digits_shown=shown,
        digits_typed=typed,
    )


def test_row_digits() -> None:
    """recall_correct jen při přesné shodě, bez číslic prázdné sloupce."""
    assert make_sample_row("4071", "4071")["recall_correct"] is True
    assert make_sample_row("4071", "4017")["recall_correct"] is False
    assert make_sample_row("4071", "")["recall_correct"] is False
    row = make_sample_row("", "")
    assert (row["digits_shown"], row["digits_typed"], row["recall_correct"]) == (
        "",
        "",
        "",
    )


@pytest.mark.parametrize("digits", ["47", "093182"])
@pytest.mark.parametrize("set_number", range(1, len(SIM_RECALL_CYCLE) + 1))
def test_sim_recall_keys_type_the_answer(digits: str, set_number: int) -> None:
    """Klávesy simulace napsané přes edit_recall dají přesně odpověď sim_recall_answer."""
    keys = sim_recall_keys(digits, set_number)
    assert keys[-1] == "return"
    typed = ""
    for name in keys[:-1]:
        typed = edit_recall(typed, name, name if len(name) == 1 else "", len(digits))
    assert typed == sim_recall_answer(digits, set_number)


def test_sim_recall_patterns() -> None:
    """Vzory simulace: správně, špatně, opraveno, kratší."""
    answers = [sim_recall_answer("093182", n) for n in range(1, 5)]
    assert answers[0] == "093182"
    assert answers[1] != "093182"
    assert len(answers[1]) == 6
    assert answers[2] == "093182"
    assert answers[3] == "0"


def test_make_sim_typed_keys() -> None:
    """Úvod, testovací kola (R mezi nimi, mezerník po posledním), pak ostré sady."""
    keys = make_sim_typed_keys([["47"], ["35"]], ["093182"])
    assert keys[: len(SIM_INTRO_KEYS)] == list(SIM_INTRO_KEYS)
    rest = keys[len(SIM_INTRO_KEYS) :]
    expected = ["space", *sim_recall_keys("47", 1), "r"]
    expected += ["space", *sim_recall_keys("35", 2), "space"]
    assert rest == expected + sim_recall_keys("093182", 3)
