from psychopy import logging

from config import (
    ANTICIPATION_THRESHOLD,
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
    REST_INTERVAL,
)
from logic import Start, make_plan

logging.console.setLevel(logging.ERROR)

from psychopy import core, visual  # noqa: E402
from psychopy.hardware import keyboard  # noqa: E402


def frames(seconds: float, rate: float) -> int:
    """Převede sekundy na počet snímků."""
    return round(seconds * rate)


def make_lamps(win: visual.Window) -> list[visual.Circle]:
    """Vytvoří zhasnuté lampy vedle sebe, souměrně kolem středu."""
    lamps = []
    for i in range(N_LAMPS):
        x = (i - (N_LAMPS - 1) / 2) * LAMP_SPACING
        lamps.append(
            visual.Circle(
                win, radius=LAMP_RADIUS, pos=(x, LAMP_Y), fillColor=OFF, lineColor=None
            )
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
        win,
        width=FLAG_WIDTH,
        height=FLAG_HEIGHT,
        pos=FLAG_POS,
        fillColor=FLAG_COLOR,
        lineColor=None,
    )


def run_start(
    win: visual.Window,
    lamps: list[visual.Circle],
    rate: float,
    kb: keyboard.Keyboard,
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
            if keys[0].rt < 0:
                return ("jump_start", None)
            if start.is_nogo:
                return ("commission", keys[0].rt)
            if keys[0].rt < ANTICIPATION_THRESHOLD:
                return ("anticipation", keys[0].rt)
            return ("go", keys[0].rt)

    if start.is_nogo:
        return ("inhibit", None)
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


def main() -> None:
    # Dočasně jen pro macOS, okno pro oba systémy řeší krok 2.
    import AppKit

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
    flag = make_flag(win)
    for start in make_plan():
        outcome, rt = run_start(win, lamps, rate, kb, flag, start)
        print(start.foreperiod, start.is_nogo, outcome, rt)
        show_pause(win, lamps, REST_INTERVAL, rate, kb)

    win.close()
    core.quit()


if __name__ == "__main__":
    main()
