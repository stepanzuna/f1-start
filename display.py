"""Okno, displej a klávesnice (PsychoPy): otevření okna, Retina, měření frekvence, prostředí.

Přesunuto z main.py beze změny kódu (refaktorizace 16. 11. 2026). Importuje se až po zapnutí
DPI awareness a ztišení logování v main.py (viz CLAUDE.md, Logování).
"""

import os
import platform
import sys
from dataclasses import dataclass
from pathlib import Path

import psychopy
import pyglet
from psychopy import core, logging, visual
from psychopy.hardware import keyboard

from config import (
    EXPECTED_FRAME_RATE,
    FRAME_RATE_TOLERANCE,
    KEYBOARD_BACKEND,
    SIM_WINDOW_MODE,
    WINDOW_MODE,
    WINDOW_MODES,
)
from logic import git_commit
from simulation import sim_window_size


def get_screen_size() -> tuple[int, int]:
    """Zjistí velikost hlavního displeje stejně jako PsychoPy (přes pyglet)."""
    screen = pyglet.canvas.get_display().get_default_screen()
    return (screen.width, screen.height)


def pixel_ratio() -> float:
    """Počet fyzických pixelů na bod displeje (Retina 2); mimo macOS 1."""
    if sys.platform == "darwin":
        import AppKit

        return float(AppKit.NSScreen.mainScreen().backingScaleFactor())
    return 1.0


def open_window(mode: str) -> visual.Window:
    """Otevře okno přes celou obrazovku ("fullscr", "borderless"), v simulaci menší."""
    if mode not in (*WINDOW_MODES, SIM_WINDOW_MODE):
        raise ValueError(f"Neznámý režim okna {mode!r}, povolené: {WINDOW_MODES}")

    windowed = mode == SIM_WINDOW_MODE
    screen = get_screen_size()
    size = sim_window_size(screen, pixel_ratio()) if windowed else screen
    win = visual.Window(
        size=size,
        pos=None if windowed else (0, 0),
        fullscr=(mode == "fullscr"),
        allowGUI=windowed,
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
    win.mouseVisible = windowed
    return win


def exit_if_hidden_launch(mode: str) -> None:
    """Ukončí program, když by okno na macOS zůstalo schované za VS Code."""
    from_vscode = os.environ.get("TERM_PROGRAM") == "vscode"
    if sys.platform == "darwin" and mode == "fullscr" and from_vscode:
        sys.exit(
            "Z terminálu VS Code zůstane okno schované a experiment by běžel naslepo.\n"
            "Spusť ho přes Cmd+Shift+B nebo z aplikace Terminál."
        )


def open_keyboard() -> keyboard.Keyboard:
    """Otevře klávesnici přes iohub; když PsychoPy použije jiný backend, ukončí program."""
    kb = keyboard.Keyboard(backend=KEYBOARD_BACKEND)
    if kb.getBackend() != KEYBOARD_BACKEND:
        sys.exit(
            f"Klávesnice běží přes {kb.getBackend()!r} místo {KEYBOARD_BACKEND!r}, "
            "měření by nebylo srovnatelné."
        )
    return kb


def measure_frame_rate(win: visual.Window) -> float:
    """Změří obnovovací frekvenci, při chybě nebo nečekané hodnotě ukončí program.

    Měří se hned po otevření okna, před zadáním nicku, takže sezení ještě nemá log:
    důvod ukončení jde přes logging do terminálu.
    """
    rate = win.getActualFrameRate()
    if rate is None:
        logging.error("Nepodařilo se změřit obnovovací frekvenci.")
        win.close()
        core.quit()
    if abs(rate - EXPECTED_FRAME_RATE) > FRAME_RATE_TOLERANCE:
        logging.error(
            f"Obnovovací frekvence je {rate:.1f} Hz, potřeba je {EXPECTED_FRAME_RATE} Hz. "
            "Nastav pevnou frekvenci displeje (macOS: Nastavení → Monitory, ne ProMotion)."
        )
        win.close()
        core.quit()
    return rate


def describe_environment(project_dir: Path) -> dict[str, str]:
    """Popíše systém a verze programů pro metadata sezení."""
    return {
        "platform": platform.platform(),
        "python_version": platform.python_version(),
        "psychopy_version": psychopy.__version__,
        "git_commit": git_commit(project_dir),
    }


@dataclass
class Display:
    """Otevřené okno a jeho vlastnosti (ukládají se do meta)."""

    win: visual.Window
    rate: float
    mode: str
    size: tuple[int, int]


def open_display(simulated: bool) -> Display:
    """Otevře okno (v simulaci menší) a změří obnovovací frekvenci."""
    window_mode = SIM_WINDOW_MODE if simulated else WINDOW_MODE
    win = open_window(window_mode)
    logging.console.setLevel(logging.WARNING)
    rate = measure_frame_rate(win)
    window_size = (int(win.size[0]), int(win.size[1]))
    print(
        f"systém {sys.platform}, režim {window_mode}, velikost okna {window_size} px, "
        f"frekvence {rate:.2f} Hz{', SIMULACE' if simulated else ''}",
        flush=True,
    )
    return Display(win, rate, window_mode, window_size)
