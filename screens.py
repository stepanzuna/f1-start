"""Obrazovky s textem a pomocné funkce pro snímky a klávesy (PsychoPy).

Přesunuto z main.py beze změny kódu (refaktorizace 14. 11. 2026). Importuje se až po
nastavení logování v main.py (viz CLAUDE.md, Logování).
"""

from collections.abc import Callable
from pathlib import Path

from psychopy import core, visual
from psychopy.hardware import keyboard

from config import (
    CALIBRATION_KEYS,
    CALIBRATION_TEXT_Y,
    CALIBRATION_VALUE_Y,
    CARD_COLOR,
    CURSOR,
    DIGITS_BLANK,
    DIGITS_DURATION,
    ENTER_KEYS,
    INPUT_Y,
    MESSAGE_Y,
    NICK_PROMPT,
    PROMPT_Y,
    TEXT_COLOR,
    TEXT_HEIGHT,
    TEXT_WRAP_SHARE,
    WARNING_COLOR,
)
from logic import (
    NickInput,
    SettingsInfo,
    adjust_card_width,
    apply_settings_key,
    calibration_accepts_enter,
    calibration_screen_text,
    calibration_value_text,
    card_height_px,
    card_width_px,
    edit_recall,
    genuine_presses,
    nick_input_key,
    px_per_cm_from_card,
    settings_action,
    settings_text,
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
    px_per_cm: float,
    y: float = 0.0,
    color: str = TEXT_COLOR,
    height: float = TEXT_HEIGHT,
) -> visual.TextStim:
    """Vytvoří prázdný text pro obrazovky s textem, zalomený podle šířky okna.

    Pozice y a výška písma jsou v cm, převedou se podle kalibrace (px_per_cm).
    """
    return visual.TextStim(
        win,
        text="",
        pos=(0, y * px_per_cm),
        height=height * px_per_cm,
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


def ask_nick(
    win: visual.Window,
    kb: AnyKeyboard,
    px_per_cm: float,
    exists: Callable[[str], bool],
) -> str:
    """Obrazovka s nickem: psaní, ověření a potvrzení už existujícího nicku."""
    prompt = make_text(win, px_per_cm, PROMPT_Y)
    set_text(prompt, NICK_PROMPT)
    typed = make_text(win, px_per_cm, INPUT_Y)
    message = make_text(win, px_per_cm, MESSAGE_Y, WARNING_COLOR)
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
    info: SettingsInfo,
    choice: tuple[str, str],
) -> tuple[str, str, str]:
    """Obrazovka nastavení: pořadí bloků (A/B) a jazyk účastníka (C/E).

    Začíná volbou choice (pořadí bloků, jazyk). Enter = začít sezení, K = kalibrace,
    V = ověření velikosti: vrátí (pořadí bloků, jazyk, akce) a po K a V se obrazovka
    ukáže znovu s dosavadní volbou.
    """
    block_order, language = choice
    screen = make_text(win, info.calibration.px_per_cm)
    kb.clearEvents()
    while True:
        for key in read_screen_keys(win, kb):
            action = settings_action(key.name)
            if action is not None:
                return block_order, language, action
            block_order, language = apply_settings_key(key.name, block_order, language)
        set_text(screen, settings_text(info, block_order, language))
        screen.draw()
        win.flip()


def ask_calibration(win: visual.Window, kb: AnyKeyboard, px_per_cm: float) -> float:
    """Kalibrace velikosti: šipky mění šířku obdélníku v poměru stran karty, Enter uloží.

    Začíná na dosavadní (nebo odhadnuté) hodnotě px_per_cm, podle ní je i písmo. Enter
    přijme jen věrohodnou hodnotu a až po úpravě šipkami. Vrátí nové pixely na centimetr.
    """
    width = card_width_px(px_per_cm)
    card = visual.Rect(
        win,
        width=width,
        height=card_height_px(width),
        fillColor=CARD_COLOR,
        lineColor=None,
        units="pix",
    )
    instructions = make_text(win, px_per_cm, CALIBRATION_TEXT_Y)
    set_text(instructions, calibration_screen_text())
    value = make_text(win, px_per_cm, CALIBRATION_VALUE_Y)
    adjusted = False
    kb.clearEvents()
    while True:
        for key in read_screen_keys(win, kb):
            if key.name in ENTER_KEYS and calibration_accepts_enter(width, adjusted):
                return px_per_cm_from_card(width)
            adjusted = adjusted or key.name in CALIBRATION_KEYS
            width = adjust_card_width(width, key.name)
            card.size = (width, card_height_px(width))
        set_text(value, calibration_value_text(width, adjusted))
        for stim in (card, instructions, value):
            stim.draw()
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
