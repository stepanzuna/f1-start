"""Čistá logika experimentu bez PsychoPy: popis startu a plán startů."""

import random
from dataclasses import dataclass

from config import FOREPERIODS, GO_PER_FOREPERIOD, NOGO_PER_FOREPERIOD


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
