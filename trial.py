"""Jeden F1 start (PsychoPy): lampy semaforu, žlutá vlajka, měřený start a pauza po něm.

Přesunuto z main.py beze změny kódu (refaktorizace 16. 11. 2026). Importuje se až po zapnutí
DPI awareness a ztišení logování v main.py (viz CLAUDE.md, Logování).
"""

from pathlib import Path

from psychopy import visual

from config import (
    FLAG_COLOR,
    FLAG_HEIGHT,
    FLAG_POS,
    FLAG_WIDTH,
    LAMP_RADIUS,
    LAMP_SPACING,
    LAMP_Y,
    LIGHT_INTERVAL,
    N_LAMPS,
    OFF,
    ON,
    RESPONSE_WINDOW,
)
from logic import Start, classify_press, outcome_without_press
from screens import AnyKeyboard, frames, quit_if_escape, save_frame, set_text


def make_lamps(win: visual.Window, px_per_cm: float) -> list[visual.Circle]:
    """Vytvoří zhasnuté lampy vedle sebe, souměrně kolem středu (rozměry z cm na pixely)."""
    lamps = []
    for i in range(N_LAMPS):
        x = (i - (N_LAMPS - 1) / 2) * LAMP_SPACING * px_per_cm
        lamps.append(
            visual.Circle(
                win,
                radius=LAMP_RADIUS * px_per_cm,
                pos=(x, LAMP_Y * px_per_cm),
                fillColor=OFF,
                lineColor=None,
            )
        )
    return lamps


def draw_lamps(lamps: list[visual.Circle], n_on: int) -> None:
    """Nakreslí lampy, prvních n_on rozsvícených."""
    for i, lamp in enumerate(lamps):
        lamp.fillColor = ON if i < n_on else OFF
        lamp.draw()


def make_flag(win: visual.Window, px_per_cm: float) -> visual.Rect:
    """Vytvoří obdélníkovou vlajku nad semaforem (rozměry z cm na pixely)."""
    return visual.Rect(
        win,
        width=FLAG_WIDTH * px_per_cm,
        height=FLAG_HEIGHT * px_per_cm,
        pos=(FLAG_POS[0] * px_per_cm, FLAG_POS[1] * px_per_cm),
        fillColor=FLAG_COLOR,
        lineColor=None,
    )


def run_start(
    win: visual.Window,
    lamps: list[visual.Circle],
    rate: float,
    kb: AnyKeyboard,
    flag: visual.Rect,
    start: Start,
) -> tuple[str, float | None]:
    """Jeden F1 start: rozsvěcování, prodleva, zhasnutí, u no-go se žlutou vlajkou."""
    kb.clearEvents()

    for n_on in range(1, N_LAMPS):
        for _ in range(frames(LIGHT_INTERVAL, rate)):
            keys = kb.getKeys(keyList=["space", "escape"], waitRelease=False)
            quit_if_escape(keys, win)
            if keys:
                return ("jump_start", None)
            draw_lamps(lamps, n_on)
            win.flip()

    for _ in range(frames(start.foreperiod, rate)):
        keys = kb.getKeys(keyList=["space", "escape"], waitRelease=False)
        quit_if_escape(keys, win)
        if keys:
            return ("jump_start", None)
        draw_lamps(lamps, N_LAMPS)
        win.flip()

    for i in range(frames(RESPONSE_WINDOW, rate)):
        if i == 0:
            win.callOnFlip(kb.clock.reset)
        draw_lamps(lamps, 0)
        if start.is_nogo:
            flag.draw()
        win.flip()

        keys = kb.getKeys(keyList=["space", "escape"], waitRelease=False)
        quit_if_escape(keys, win)
        if keys:
            outcome = classify_press(keys[0].rt, start.is_nogo)
            return (outcome, None if outcome == "jump_start" else keys[0].rt)

    return (outcome_without_press(start.is_nogo), None)


def show_pause(
    win: visual.Window,
    lamps: list[visual.Circle],
    rest_time: float,
    rate: float,
    kb: AnyKeyboard,
    feedback: visual.TextStim,
    message: str,
    capture_path: Path | None = None,
) -> None:
    """Pauza mezi starty se zpětnou vazbou (zhasnuté lampy a hláška).

    S capture_path (jen simulace) uloží první snímek pauzy jako obrázek.
    """
    set_text(feedback, message)  # jednou před pauzou, překreslení textu je pomalé
    for i in range(frames(rest_time, rate)):
        quit_if_escape(kb.getKeys(keyList=["escape"], waitRelease=False), win)
        draw_lamps(lamps, 0)
        feedback.draw()
        if i == 0 and capture_path is not None:
            save_frame(win, capture_path)
        win.flip()
