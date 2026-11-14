"""Testy průběhu sezení: bloky, Paasova škála a závěrečné zhodnocení (bez okna PsychoPy)."""

from datetime import datetime, timedelta, timezone

import pytest

from config import LANGUAGES, TEXTS
from logic import (
    Start,
    build_session,
    effort_rating,
    make_row,
    session_summary,
    split_blocks,
)

SAMPLE_TIME = datetime(2026, 11, 14, 9, 0, tzinfo=timezone(timedelta(hours=1)))


def test_split_blocks() -> None:
    """Plán sezení se rozdělí na 4 bloky v pořadí, každý se svou zátěží."""
    plan, _ = build_session("ABBA", 1, short=False)
    blocks = split_blocks(plan)
    assert [block[0].block for block in blocks] == [1, 2, 3, 4]
    assert [block[0].load for block in blocks] == ["low", "high", "high", "low"]
    assert sum(len(block) for block in blocks) == len(plan)


@pytest.mark.parametrize(
    ("char", "rating"),
    [("1", 1), ("9", 9), ("ž", 6), ("Ž", 6), ("0", None), ("a", None), ("", None)],
)
def test_effort_rating(char: str, rating: int | None) -> None:
    """Hodnocení 1–9 i z české horní řady; 0 a ostatní znaky ne."""
    assert effort_rating(char) == rating


LOADS_BY_BLOCK = {0: "low", 1: "low", 2: "high"}


def rows_for(results: list[tuple[int, int, bool, str, float | None, str, str]]) -> list:
    """Řádky z make_row: (blok, sada, no-go, výsledek, rt, číslice, odpověď)."""
    rows = []
    for index, (block, set_index, nogo, outcome, rt, shown, typed) in enumerate(
        results
    ):
        start = Start(0.5, nogo, LOADS_BY_BLOCK[block], block, set_index, 1)
        rows.append(
            make_row(
                "anna",
                "mac",
                start,
                index + 1,
                outcome,
                rt,
                0,
                SAMPLE_TIME,
                shown,
                typed,
            )
        )
    return rows


def test_session_summary() -> None:
    """Průměr go, předčasné starty, vlajka z no-go, správné sady podle zátěže; bez tréninku."""
    rows = rows_for(
        [
            (0, 5, False, "go", 0.9, "12", "12"),  # testovací kolo se nepočítá
            (1, 1, False, "go", 0.2, "47", "47"),
            (1, 1, False, "anticipation", 0.05, "47", "47"),
            (1, 1, True, "commission", 0.3, "47", "47"),
            (1, 2, False, "go", 0.3, "35", "53"),
            (1, 2, False, "jump_start", None, "35", "53"),
            (1, 2, True, "inhibit", None, "35", "53"),
            (2, 1, False, "go", 0.4, "093182", "093182"),
        ]
    )
    summary = session_summary(rows)
    assert summary == {
        "mean_rt": "300",
        "false_starts": 2,
        "starts": 7,
        "commissions": 1,
        "nogo": 2,
        "recall_low": "50",
        "recall_high": "100",
    }


def test_session_summary_empty_and_text() -> None:
    """Bez dat pomlčky; text závěru jde vyplnit v obou jazycích."""
    summary = session_summary([])
    assert summary["mean_rt"] == "–"
    for language in LANGUAGES:
        text = TEXTS[language]["end"].format(**summary)
        assert "–" in text
