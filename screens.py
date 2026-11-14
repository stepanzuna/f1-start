"""Obrazovky s textem a pomocné funkce pro snímky a klávesy (PsychoPy).

Přesunuto z main.py beze změny kódu (refaktorizace 14. 11. 2026). Importuje se až po
nastavení logování v main.py (viz CLAUDE.md, Logování).
"""

from collections.abc import Callable
from pathlib import Path

from psychopy import core, visual
from psychopy.hardware import keyboard

from config import (
    CURSOR,
    DEFAULT_LANGUAGE,
    DIGITS_BLANK,
    DIGITS_DURATION,
    ENTER_KEYS,
    FOLDER_NOTE,
    INPUT_Y,
    LANGUAGE_NAMES,
    MESSAGE_Y,
    NICK_PROMPT,
    PROMPT_Y,
    SETTINGS_SCREEN,
    TEXT_COLOR,
    TEXT_HEIGHT,
    TEXT_WRAP_SHARE,
    WARNING_COLOR,
)
from logic import (
    NickInput,
    apply_settings_key,
    assign_block_order,
    edit_recall,
    genuine_presses,
    nick_input_key,
    settings_order_note,
)
from simulation import (
    SimulatedKeyboard,
    SimulatedKeyPress,
)

# Program čte klávesy buď ze skutečné klávesnice (iohub), nebo ze simulace se stejným rozhraním.
AnyKeyboard = keyboard.Keyboard | SimulatedKeyboard
AnyKeyPress = keyboard.KeyPress | SimulatedKeyPress


def frames(seconds: float, rate: float) -> int:
    """Převede sekundy na počet snímků."""
    return round(seconds * rate)


def save_frame(win: visual.Window, path: Path) -> None:
    """Uloží nakreslený (ještě nezobrazený) snímek okna jako obrázek (jen simulace)."""
    win.getMovieFrame(buffer="back")
    win.saveMovieFrames(str(path))


def show_digits(
    win: visual.Window,
    kb: AnyKeyboard,
    digits_stim: visual.TextStim,
    digits: str,
    rate: float,
    capture_path: Path | None = None,
) -> None:
    """Číslice sady na DIGITS_DURATION, pak prázdná obrazovka na DIGITS_BLANK."""
    set_text(digits_stim, " ".join(digits))
    for i in range(frames(DIGITS_DURATION, rate)):
        quit_if_escape(kb.getKeys(keyList=["escape"], waitRelease=False), win)
        digits_stim.draw()
        if i == 0 and capture_path is not None:
            save_frame(win, capture_path)
        win.flip()
    for _ in range(frames(DIGITS_BLANK, rate)):
        quit_if_escape(kb.getKeys(keyList=["escape"], waitRelease=False), win)
        win.flip()


def ask_recall(
    win: visual.Window,
    kb: AnyKeyboard,
    prompt: visual.TextStim,
    typed: visual.TextStim,
    prompt_text: str,
    n_digits: int,
    capture_path: Path | None = None,
) -> str:
    """Vybavení: účastník napíše číslice (bez časového limitu), Enter potvrdí."""
    set_text(prompt, prompt_text)
    answer = ""
    kb.clearEvents()
    first_frame = True
    while True:
        for key in read_screen_keys(win, kb):
            if key.name in ENTER_KEYS:
                return answer
            answer = edit_recall(answer, key.name, key.code or "", n_digits)
        set_text(typed, " ".join(answer + CURSOR))
        prompt.draw()
        typed.draw()
        if first_frame and capture_path is not None:
            save_frame(win, capture_path)
        first_frame = False
        win.flip()


def quit_if_escape(keys: list[AnyKeyPress], win: visual.Window) -> None:
    """Ukončí program v libovolné chvíli při stisku esc."""
    if any(key.name == "escape" for key in keys):
        win.close()
        core.quit()


def make_text(
    win: visual.Window,
    y: int = 0,
    color: str = TEXT_COLOR,
    height: int = TEXT_HEIGHT,
) -> visual.TextStim:
    """Vytvoří prázdný text pro obrazovky s textem, zalomený podle šířky okna."""
    return visual.TextStim(
        win,
        text="",
        pos=(0, y),
        height=height,
        wrapWidth=win.size[0] * TEXT_WRAP_SHARE,
        color=color,
        units="pix",
    )


def read_screen_keys(win: visual.Window, kb: AnyKeyboard) -> list[AnyKeyPress]:
    """Klávesy na obrazovce s textem: všechny (bez keyList), bez fantomů, s Escapem.

    _keysStillDown je interní seznam držených kláves v PsychoPy 2026.2 (viz genuine_presses).
    """
    keys = kb.getKeys(waitRelease=False)
    quit_if_escape(keys, win)
    return genuine_presses(keys, getattr(kb, "_keysStillDown", None))


def set_text(stim: visual.TextStim, text: str) -> None:
    """Změní text, jen když je jiný (překreslení textu v PsychoPy je pomalé)."""
    if stim.text != text:
        stim.text = text


def ask_nick(win: visual.Window, kb: AnyKeyboard, exists: Callable[[str], bool]) -> str:
    """Obrazovka s nickem: psaní, ověření a potvrzení už existujícího nicku."""
    prompt = make_text(win, PROMPT_Y)
    set_text(prompt, NICK_PROMPT)
    typed = make_text(win, INPUT_Y)
    message = make_text(win, MESSAGE_Y, WARNING_COLOR)
    state = NickInput()
    kb.clearEvents()
    while not state.done:
        for key in read_screen_keys(win, kb):
            state = nick_input_key(state, key.name, key.code or "", exists)
            if state.done:
                break
        set_text(typed, state.text + CURSOR)
        set_text(message, state.message)
        for stim in (prompt, typed, message):
            stim.draw()
        win.flip()
    return state.text


def ask_settings(
    win: visual.Window,
    kb: AnyKeyboard,
    nick: str,
    machine: str,
    completed: int,
    folder: str,
) -> tuple[str, str]:
    """Obrazovka nastavení: pořadí bloků (A/B) a jazyk účastníka (C/E), Enter = začít."""
    auto_order = assign_block_order(completed)
    block_order = auto_order
    language = DEFAULT_LANGUAGE
    screen = make_text(win)
    kb.clearEvents()
    while True:
        for key in read_screen_keys(win, kb):
            if key.name in ENTER_KEYS:
                return block_order, language
            block_order, language = apply_settings_key(key.name, block_order, language)
        set_text(
            screen,
            SETTINGS_SCREEN.format(
                nick=nick,
                machine=machine,
                folder=FOLDER_NOTE[folder],
                block_order=block_order,
                order_note=settings_order_note(block_order, auto_order, completed),
                language_name=LANGUAGE_NAMES[language],
            ),
        )
        screen.draw()
        win.flip()


def show_message(
    win: visual.Window,
    kb: AnyKeyboard,
    stim: visual.TextStim,
    text: str,
    duration: float,
    rate: float,
    capture_path: Path | None = None,
) -> None:
    """Text na danou dobu (ve snímcích), Escape v každém snímku."""
    set_text(stim, text)
    for i in range(frames(duration, rate)):
        quit_if_escape(kb.getKeys(keyList=["escape"], waitRelease=False), win)
        stim.draw()
        if i == 0 and capture_path is not None:
            save_frame(win, capture_path)
        win.flip()
