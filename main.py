import random

import AppKit
from psychopy import logging

logging.console.setLevel(logging.ERROR)

from psychopy import core, visual  # noqa: E402
from psychopy.hardware import keyboard  # noqa: E402

OFF = "#333333"
ON = "red"
FLAG_COLOR = "#EF9F27"

FOREPERIODS = [0.5, 1.25, 2.0, 2.75]
LIGHT_INTERVAL = 1.0
RESPONSE_WINDOW = 1.5
REST_INTERVAL = 1.0
ANTICIPATION_THRESHOLD = 0.1

N_STARTS = 5
GO_PER_FOREPERIOD = 3
NOGO_PER_FOREPERIOD = 1


def frames(seconds: float, rate: float) -> int:
    """Převede sekundy na počet snímků."""
    return round(seconds * rate)


def make_lamps(win: visual.Window) -> list[visual.Circle]:
    """Vytvoří 5 zhasnutých lamp vedle sebe."""
    lamps = []
    for i in range(5):
        x = -240 + i * 120
        lamps.append(
            visual.Circle(win, radius=40, pos=(x, -90), fillColor=OFF, lineColor=None)
        )
    return lamps


def draw_lamps(lamps: list[visual.Circle], n_on: int) -> None:
    """Nakreslí lampy, prvních n_on rozsvícených."""
    for i, lamp in enumerate(lamps):
        lamp.fillColor = ON if i < n_on else OFF
        lamp.draw()


def make_flag(win: visual.Window) -> visual.Rect:
    """Vytvoří obdélníkovou vlajku nad semaforem."""
    return visual.Rect(
        win, width=500, height=300, pos=(0, 180), fillColor=FLAG_COLOR, lineColor=None
    )


def run_start(
    win: visual.Window, lamps: list[visual.Circle], rate: float, kb: keyboard.Keyboard
) -> tuple[str, float | None]:
    """Jeden F1 start: rozsvěcování, prodleva, zhasnutí."""
    kb.clearEvents()

    for n_on in range(1, 5):
        for _ in range(frames(LIGHT_INTERVAL, rate)):
            keys = kb.getKeys(keyList=["space", "escape"], waitRelease=False)
            quit_if_escape(keys, win)
            if keys:
                return ("jump_start", None)
            draw_lamps(lamps, n_on)
            win.flip()

    foreperiod = random.choice(FOREPERIODS)
    for _ in range(frames(foreperiod, rate)):
        keys = kb.getKeys(keyList=["space", "escape"], waitRelease=False)
        quit_if_escape(keys, win)
        if keys:
            return ("jump_start", None)
        draw_lamps(lamps, 5)
        win.flip()

    for i in range(frames(RESPONSE_WINDOW, rate)):
        if i == 0:
            win.callOnFlip(kb.clock.reset)
        draw_lamps(lamps, 0)
        win.flip()

        keys = kb.getKeys(keyList=["space", "escape"], waitRelease=False)
        quit_if_escape(keys, win)
        if keys:
            if keys[0].rt < 0:
                return ("jump_start", None)
            if keys[0].rt < ANTICIPATION_THRESHOLD:
                return ("anticipation", keys[0].rt)
            else:
                return ("go", keys[0].rt)

    return ("omission", None)


def show_pause(
    win: visual.Window,
    lamps: list[visual.Circle],
    rest_time: float,
    rate: float,
    kb: keyboard.Keyboard,
) -> None:
    """Vykreslení pauzy mezi jednotlivými starty."""
    for _ in range(frames(rest_time, rate)):
        quit_if_escape(kb.getKeys(keyList=["escape"], waitRelease=False), win)
        draw_lamps(lamps, 0)
        win.flip()


def quit_if_escape(keys: list[keyboard.KeyPress], win: visual.Window) -> None:
    """Ukončí program v libovolné chvíli při stisku esc."""
    if any(key.name == "escape" for key in keys):
        win.close()
        core.quit()


def make_plan() -> list[tuple[float, bool]]:
    """Vytvoří zamíchaný plán startů jako dvojice (prodleva, je no-go)."""
    plan = []
    for foreperiod in FOREPERIODS:
        for _ in range(GO_PER_FOREPERIOD):
            plan.append((foreperiod, False))
        for _ in range(NOGO_PER_FOREPERIOD):
            plan.append((foreperiod, True))
    random.shuffle(plan)
    return plan


def main() -> None:
    kb = keyboard.Keyboard(backend="iohub")

    screen = AppKit.NSScreen.screens()[0].frame().size
    win = visual.Window(
        size=(int(screen.width), int(screen.height)),
        pos=(0, 0),
        allowGUI=False,
        color="black",
        units="pix",
    )
    AppKit.NSApplication.sharedApplication().setPresentationOptions_(
        AppKit.NSApplicationPresentationHideDock
        | AppKit.NSApplicationPresentationHideMenuBar
    )
    logging.console.setLevel(logging.WARNING)
    win.winHandle.activate()
    win.mouseVisible = False
    rate = win.getActualFrameRate()
    if rate is None:
        print("Nepodařilo se změřit obnovovací frekvenci.")
        win.close()
        core.quit()

    lamps = make_lamps(win)
    for _ in range(N_STARTS):
        print(run_start(win, lamps, rate, kb))
        show_pause(win, lamps, REST_INTERVAL, rate, kb)

    win.close()
    core.quit()


if __name__ == "__main__":
    main()
