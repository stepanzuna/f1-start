"""Testy plánu sezení: počty, poměr no-go, bloky, sady, pravidlo max 2 no-go, seed."""

import random
from collections import Counter

import pytest

from config import (
    BLOCK_LOADS,
    BLOCK_ORDERS,
    DIGITS_PER_LOAD,
    FOREPERIODS,
    GO_PER_FOREPERIOD,
    MAX_NOGO_RUN,
    NOGO_PER_FOREPERIOD,
    SEED_MAX,
    SHORT_SETS_PER_BLOCK,
    STARTS_PER_SET,
)
from logic import (
    Start,
    build_session,
    longest_nogo_run,
    make_seed,
    short_plan_allowed,
    split_nogo,
)

SEEDS = range(40)
N_BLOCKS_IN_ORDER = 4
STARTS_PER_CONDITION = len(FOREPERIODS) * (GO_PER_FOREPERIOD + NOGO_PER_FOREPERIOD)


def blocks(plan: list[Start]) -> dict[int, list[Start]]:
    """Starty plánu rozdělené podle bloku."""
    result: dict[int, list[Start]] = {}
    for start in plan:
        result.setdefault(start.block, []).append(start)
    return result


@pytest.mark.parametrize("order", BLOCK_ORDERS)
def test_session_structure(order: str) -> None:
    """96 startů ve 4 blocích po 24, zátěž bloků podle pořadí, 8 sad po 3 startech."""
    plan, _ = build_session(order, 1, short=False)
    assert len(plan) == 2 * STARTS_PER_CONDITION == 96
    by_block = blocks(plan)
    assert sorted(by_block) == [1, 2, 3, 4]
    for block, starts in by_block.items():
        assert len(starts) == STARTS_PER_CONDITION // 2
        assert {start.load for start in starts} == {BLOCK_LOADS[order[block - 1]]}
        positions = [(start.set_index, start.start_in_set) for start in starts]
        n_sets = len(starts) // STARTS_PER_SET
        assert positions == [
            (s, i) for s in range(1, n_sets + 1) for i in range(1, STARTS_PER_SET + 1)
        ]


@pytest.mark.parametrize("seed", SEEDS)
def test_counts_per_condition_and_block(seed: int) -> None:
    """Podmínka: každá prodleva 9 go + 3 no-go; blok: každá prodleva 6×, no-go 25 %."""
    plan, _ = build_session("ABBA", seed, short=False)
    for load in BLOCK_LOADS.values():
        starts = [start for start in plan if start.load == load]
        counts = Counter((start.foreperiod, start.is_nogo) for start in starts)
        for fp in FOREPERIODS:
            assert counts[(fp, False)] == GO_PER_FOREPERIOD
            assert counts[(fp, True)] == NOGO_PER_FOREPERIOD
    for starts in blocks(plan).values():
        per_fp = Counter(start.foreperiod for start in starts)
        assert set(per_fp.values()) == {(GO_PER_FOREPERIOD + NOGO_PER_FOREPERIOD) // 2}
        assert sum(start.is_nogo for start in starts) * 4 == len(starts)


@pytest.mark.parametrize("seed", SEEDS)
def test_max_nogo_run_in_each_block(seed: int) -> None:
    """V žádném bloku nejsou víc než 2 no-go za sebou."""
    plan, _ = build_session("BAAB", seed, short=False)
    for starts in blocks(plan).values():
        assert longest_nogo_run(starts) <= MAX_NOGO_RUN


def test_longest_nogo_run() -> None:
    """Délka nejdelší řady no-go."""
    kinds = [False, True, True, False, True, True, True, False]
    starts = [Start(0.5, is_nogo, "low", 1, 1, 1) for is_nogo in kinds]
    assert longest_nogo_run(starts) == 3
    assert longest_nogo_run([]) == 0


def test_split_nogo() -> None:
    """Dvě prodlevy mají v prvním bloku 2 no-go, dvě 1; druhý blok obráceně."""
    first, second = split_nogo(random.Random(5))
    assert sorted(first.values()) == [1, 1, 2, 2]
    for fp in FOREPERIODS:
        assert first[fp] + second[fp] == NOGO_PER_FOREPERIOD


def test_same_seed_same_session() -> None:
    """Stejný seed a pořadí = stejný plán i číslice; jiný seed = jiný plán."""
    assert build_session("ABBA", 7, short=False) == build_session(
        "ABBA", 7, short=False
    )
    assert (
        build_session("ABBA", 7, short=False)[0] != build_session("ABBA", 8, False)[0]
    )


def test_digits_match_loads() -> None:
    """Každá sada má číslice podle zátěže svého bloku."""
    plan, digits = build_session("ABBA", 3, short=False)
    for start in plan:
        assert (
            len(digits[(start.block, start.set_index)]) == DIGITS_PER_LOAD[start.load]
        )


def test_short_plan() -> None:
    """Zkrácený plán: z každého bloku první sada (12 startů), stejné starty i číslice."""
    full_plan, full_digits = build_session("BAAB", 9, short=False)
    short_plan, short_digits = build_session("BAAB", 9, short=True)
    expected = N_BLOCKS_IN_ORDER * SHORT_SETS_PER_BLOCK * STARTS_PER_SET
    assert len(short_plan) == expected
    assert short_plan == [s for s in full_plan if s.set_index <= SHORT_SETS_PER_BLOCK]
    assert short_digits == full_digits


def test_make_seed() -> None:
    """Seed je celé číslo v povoleném rozsahu."""
    seeds = {make_seed() for _ in range(20)}
    assert all(0 <= seed < SEED_MAX for seed in seeds)
    assert len(seeds) > 1


@pytest.mark.parametrize("seed", SEEDS)
def test_nogo_split_in_each_block(seed: int) -> None:
    """V každém bloku mají dvě prodlevy 2 no-go a dvě 1 no-go."""
    plan, _ = build_session("ABBA", seed, short=False)
    for starts in blocks(plan).values():
        nogo = Counter(start.foreperiod for start in starts if start.is_nogo)
        assert sorted(nogo[fp] for fp in FOREPERIODS) == [1, 1, 2, 2]


def test_make_block_gives_up_instead_of_hanging(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Nesplnitelné pravidlo skončí srozumitelnou chybou, ne nekonečnou smyčkou."""
    import logic

    monkeypatch.setattr(logic, "MAX_NOGO_RUN", -1)
    monkeypatch.setattr(logic, "MAX_SHUFFLES", 50)
    with pytest.raises(RuntimeError, match="nepodařilo zamíchat"):
        build_session("ABBA", 1, short=False)


@pytest.mark.parametrize(
    ("simulated", "nick", "allowed"),
    [
        (True, "sim", True),
        (False, "test_x", True),
        (False, "anna", False),
        (False, "pilot1", False),
    ],
)
def test_short_plan_allowed(simulated: bool, nick: str, allowed: bool) -> None:
    """Zkrácený plán jen pro simulaci a testovací nick."""
    assert short_plan_allowed(simulated, nick) is allowed
