"""Testy čisté logiky experimentu (bez PsychoPy)."""

from config import FOREPERIODS, GO_PER_FOREPERIOD, NOGO_PER_FOREPERIOD
from logic import make_plan


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
