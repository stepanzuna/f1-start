"""Úvod sezení (PsychoPy): kalibrace, ověření velikosti, nick, nastavení a cesta k datům.

Přesunuto z main.py beze změny kódu (refaktorizace 16. 11. 2026). Importuje se až po zapnutí
DPI awareness a ztišení logování v main.py (viz CLAUDE.md, Logování).
"""

import sys
from dataclasses import dataclass, replace
from datetime import datetime
from pathlib import Path

from psychopy import visual

from config import (
    DEFAULT_LANGUAGE,
    ENTER_KEYS,
    N_LAMPS,
    SETTINGS_CALIBRATE,
    SETTINGS_START,
    SIZE_CHECK_TEXT_Y,
    TEST_PREFIX,
)
from logic import (
    Calibration,
    MachineInfo,
    RunOptions,
    SettingsInfo,
    assign_block_order,
    calibration_for_window,
    make_data_path,
    nick_exists,
    provisional_px_per_cm,
    recalibrated,
    session_data_dir,
    short_plan_allowed,
    size_check_text,
)
from screens import (
    AnyKeyboard,
    ask_calibration,
    ask_nick,
    ask_settings,
    make_text,
    read_screen_keys,
    set_text,
    window_size_pix,
)
from trial import draw_lamps, make_flag, make_lamps


@dataclass
class Participant:
    """Co experimentátor zadal na úvodních obrazovkách."""

    nick: str
    data_dir: Path
    block_order: str
    language: str
    calibration: Calibration


def calibrate(
    win: visual.Window,
    kb: AnyKeyboard,
    window_size: tuple[int, int],
    previous: Calibration | None,
) -> Calibration:
    """Kalibrační obrazovka pro tuto velikost okna.

    Začíná na dosavadní kalibraci, bez ní na odhadu z viditelné výšky okna. Beze změny
    hodnoty zůstane dosavadní kalibrace i s datem (recalibrated).
    """
    if previous is None:
        start = provisional_px_per_cm(window_size_pix(win)[1])
    else:
        start = previous.px_per_cm
    measured = ask_calibration(win, kb, start)
    calibrated_at = datetime.now().astimezone().isoformat(timespec="seconds")
    print(f"kalibrace: {measured} px/cm", flush=True)
    return recalibrated(previous, measured, window_size, calibrated_at)


def ensure_calibration(
    win: visual.Window,
    kb: AnyKeyboard,
    machine_info: MachineInfo,
    window_size: tuple[int, int],
) -> Calibration:
    """Uložená kalibrace pro tuto velikost okna, jinak kalibrační obrazovka hned (před nickem)."""
    calibration = calibration_for_window(machine_info, window_size)
    if calibration is not None:
        return calibration
    return calibrate(win, kb, window_size, None)


def show_size_check(win: visual.Window, kb: AnyKeyboard, px_per_cm: float) -> None:
    """Vlajka a rozsvícené lampy v kalibrované velikosti k ověření pravítkem; Enter = zpět."""
    lamps = make_lamps(win, px_per_cm)
    flag = make_flag(win, px_per_cm)
    text = make_text(win, px_per_cm, SIZE_CHECK_TEXT_Y)
    set_text(text, size_check_text())
    kb.clearEvents()
    while True:
        flag.draw()
        draw_lamps(lamps, N_LAMPS)
        text.draw()
        win.flip()
        if any(key.name in ENTER_KEYS for key in read_screen_keys(win, kb)):
            return


def ask_participant(
    win: visual.Window,
    kb: AnyKeyboard,
    options: RunOptions,
    data_root: Path,
    info: SettingsInfo,
) -> Participant:
    """Úvodní obrazovky: nick (a kontrola --short), pak nastavení.

    info je počítač a kalibrace (nick a složku doplní obrazovka s nickem). Na nastavení
    K = kalibrovat znovu, V = ověřit velikost; pak se nastavení vrátí s dosavadní volbou.
    """

    def exists(nick: str) -> bool:
        """Existuje už sezení s tímto nickem? V simulaci se nekontroluje."""
        return not options.simulated and nick_exists(
            session_data_dir(data_root, options.simulated, nick), nick
        )

    nick = ask_nick(win, kb, info.calibration.px_per_cm, exists)
    if options.short and not short_plan_allowed(options.simulated, nick):
        win.close()
        sys.exit(
            f"Zkrácený plán (--short) je jen pro testy: nick musí začínat "
            f"{TEST_PREFIX!r}, nebo spusť simulaci. Nick {nick!r} by šel mezi ostrá data."
        )
    data_dir = session_data_dir(data_root, options.simulated, nick)
    folder = "" if data_dir == data_root else data_dir.name
    info = replace(info, nick=nick, folder=folder)
    choice = (assign_block_order(info.completed), DEFAULT_LANGUAGE)
    while True:
        block_order, language, action = ask_settings(win, kb, info, choice)
        choice = (block_order, language)
        if action == SETTINGS_START:
            return Participant(nick, data_dir, block_order, language, info.calibration)
        calibration = info.calibration
        if action == SETTINGS_CALIBRATE:
            calibration = calibrate(win, kb, calibration.window_size, calibration)
            info = replace(info, calibration=calibration)
        else:
            show_size_check(win, kb, calibration.px_per_cm)


def create_data_path(
    win: visual.Window, participant: Participant, machine: str, started_at: datetime
) -> Path:
    """Složka a název CSV sezení; stejný nick ve stejné minutě ukončí program."""
    participant.data_dir.mkdir(parents=True, exist_ok=True)
    data_path = make_data_path(
        participant.data_dir, participant.nick, machine, started_at
    )
    if data_path.exists():
        win.close()
        sys.exit(
            f"Soubor {data_path.name} už existuje (stejný nick ve stejné minutě).\n"
            "Počkej minutu a spusť experiment znovu."
        )
    return data_path
