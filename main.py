import os
import sys

from psychopy import logging

from config import (
    ANTICIPATION_THRESHOLD,
    EXPECTED_FRAME_RATE,
    FLAG_COLOR,
    FLAG_HEIGHT,
    FLAG_POS,
    FLAG_WIDTH,
    FRAME_RATE_TOLERANCE,
    LAMP_RADIUS,
    LAMP_SPACING,
    LAMP_Y,
    LIGHT_INTERVAL,
    N_LAMPS,
    OFF,
    ON,
    RESPONSE_WINDOW,
    REST_INTERVAL,
    WINDOW_MODE,
    WINDOW_MODES,
)
from logic import Start, make_plan

logging.console.setLevel(logging.ERROR)

import pyglet  # noqa: E402
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


def get_screen_size() -> tuple[int, int]:
    """Zjistí velikost hlavního displeje stejně jako PsychoPy (přes pyglet)."""
    screen = pyglet.canvas.get_display().get_default_screen()
    return (screen.width, screen.height)


def open_window(mode: str) -> visual.Window:
    """Otevře okno přes celou obrazovku v režimu "fullscr" nebo "borderless"."""
    if mode not in WINDOW_MODES:
        raise ValueError(f"Neznámý režim okna {mode!r}, povolené: {WINDOW_MODES}")

    win = visual.Window(
        size=get_screen_size(),
        pos=(0, 0),
        fullscr=(mode == "fullscr"),
        allowGUI=False,
        color="black",
        units="pix",
    )
    if mode == "borderless" and sys.platform == "darwin":
        import AppKit

        AppKit.NSApplication.sharedApplication().setPresentationOptions_(
            AppKit.NSApplicationPresentationHideDock
            | AppKit.NSApplicationPresentationHideMenuBar
        )
    win.winHandle.activate()
    win.mouseVisible = False
    return win


def exit_if_hidden_launch(mode: str) -> None:
    """Ukončí program, když by okno na macOS zůstalo schované za VS Code."""
    from_vscode = os.environ.get("TERM_PROGRAM") == "vscode"
    if sys.platform == "darwin" and mode == "fullscr" and from_vscode:
        sys.exit(
            "Z terminálu VS Code zůstane okno schované a experiment by běžel naslepo.\n"
            "Spusť ho přes Cmd+Shift+B nebo z aplikace Terminál."
        )


def measure_frame_rate(win: visual.Window) -> float:
    """Změří obnovovací frekvenci, při chybě nebo nečekané hodnotě ukončí program."""
    rate = win.getActualFrameRate()
    if rate is None:
        print("Nepodařilo se změřit obnovovací frekvenci.")
        win.close()
        core.quit()
    if abs(rate - EXPECTED_FRAME_RATE) > FRAME_RATE_TOLERANCE:
        print(
            f"Obnovovací frekvence je {rate:.1f} Hz, potřeba je {EXPECTED_FRAME_RATE} Hz.\n"
            "Nastav pevnou frekvenci displeje (macOS: Nastavení → Monitory, ne ProMotion)."
        )
        win.close()
        core.quit()
    return rate


def main() -> None:
    exit_if_hidden_launch(WINDOW_MODE)
    kb = keyboard.Keyboard(backend="iohub")

    win = open_window(WINDOW_MODE)
    logging.console.setLevel(logging.WARNING)
    rate = measure_frame_rate(win)
    print(
        f"systém {sys.platform}, režim {WINDOW_MODE}, velikost okna {win.size} px, "
        f"frekvence {rate:.2f} Hz",
        flush=True,
    )

    lamps = make_lamps(win)
    flag = make_flag(win)
    win.recordFrameIntervals = True
    for start in make_plan():
        dropped_before = win.nDroppedFrames
        outcome, rt = run_start(win, lamps, rate, kb, flag, start)
        dropped = win.nDroppedFrames - dropped_before
        print(
            start.foreperiod,
            start.is_nogo,
            outcome,
            rt,
            f"vypadlé snímky: {dropped} (celkem {win.nDroppedFrames})",
        )
        show_pause(win, lamps, REST_INTERVAL, rate, kb)

    win.close()
    core.quit()


if __name__ == "__main__":
    main()
