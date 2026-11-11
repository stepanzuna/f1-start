import random

from psychopy import logging

logging.console.setLevel(logging.ERROR)

from psychopy import core, visual
from psychopy.hardware import keyboard

OFF = "#333333"
ON = "red"
FOREPERIODS = [0.5, 1.25, 2.0, 2.75]
LIGHT_INTERVAL = 1.0
RESPONSE_WINDOW = 2.0
REST_INTERVAL = 1.0
N_STARTS = 5


def frames(seconds: float, rate: float) -> int:
    """Převede sekundy na počet snímků."""
    return round(seconds * rate)


def make_lamps(win: visual.Window) -> list[visual.Circle]:
    """Vytvoří 5 zhasnutých lamp vedle sebe."""
    lamps = []
    for i in range(5):
        x = -240 + i * 120
        lamps.append(
            visual.Circle(win, radius=40, pos=(x, 0), fillColor=OFF, lineColor=None)
        )
    return lamps


def draw_lamps(lamps: list[visual.Circle], n_on: int) -> None:
    """Nakreslí lampy, prvních n_on rozsvícených."""
    for i, lamp in enumerate(lamps):
        lamp.fillColor = ON if i < n_on else OFF
        lamp.draw()


def run_start(
    win: visual.Window, lamps: list[visual.Circle], rate: float, kb: keyboard.Keyboard
) -> tuple[str, float | None]:
    """Jeden F1 start: rozsvěcování, prodleva, zhasnutí."""
    kb.clearEvents()

    for n_on in range(1, 5):
        for _ in range(frames(LIGHT_INTERVAL, rate)):
            keys = kb.getKeys(keyList=["space"], waitRelease=False)
            if keys:
                return ("jump start", None)
            draw_lamps(lamps, n_on)
            win.flip()

    foreperiod = random.choice(FOREPERIODS)
    for _ in range(frames(foreperiod, rate)):
        keys = kb.getKeys(keyList=["space"], waitRelease=False)
        if keys:
            return ("jump start", None)
        draw_lamps(lamps, 5)
        win.flip()

    for i in range(frames(RESPONSE_WINDOW, rate)):
        if i == 0:
            win.callOnFlip(kb.clock.reset)
        draw_lamps(lamps, 0)
        win.flip()

        keys = kb.getKeys(keyList=["space"], waitRelease=False)
        if keys:
            if keys[0].rt < 0.14:
                return ("jump start", None)
            else:
                return ("go", keys[0].rt)

    return ("omission", None)


def show_pause(
    win: visual.Window, lamps: list[visual.Circle], rest_time: float, rate: float
) -> None:
    """Vykreslení pauzy mezi jednotlivými starty."""
    for _ in range(frames(rest_time, rate)):
        draw_lamps(lamps, 0)
        win.flip()


def main() -> None:
    kb = keyboard.Keyboard(backend="iohub")

    win = visual.Window(size=(800, 600), color="black", units="pix")
    logging.console.setLevel(logging.WARNING)
    win.winHandle.activate()
    win.mouseVisible = False
    rate = win.getActualFrameRate()

    lamps = make_lamps(win)
    for _ in range(N_STARTS):
        print(run_start(win, lamps, rate, kb))
        show_pause(win, lamps, REST_INTERVAL, rate)

    win.close()
    core.quit()


if __name__ == "__main__":
    main()
