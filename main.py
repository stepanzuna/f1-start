import csv
import os
import platform
import sys
from collections.abc import Callable
from datetime import datetime
from pathlib import Path

import psychopy
from psychopy import logging

from config import (
    CSV_COLUMNS,
    CURSOR,
    DATA_DIR_NAME,
    DEFAULT_LANGUAGE,
    DROPPED_FRAME_WARNINGS_MAX,
    ENTER_KEYS,
    EXPECTED_FRAME_RATE,
    FLAG_COLOR,
    FLAG_HEIGHT,
    FLAG_POS,
    FLAG_WIDTH,
    FOLDER_NOTE,
    FRAME_RATE_TOLERANCE,
    INPUT_Y,
    KEYBOARD_BACKEND,
    LAMP_RADIUS,
    LAMP_SPACING,
    LAMP_Y,
    LANGUAGE_NAMES,
    LIGHT_INTERVAL,
    LOG_SUFFIX,
    MESSAGE_Y,
    META_SUFFIX,
    N_LAMPS,
    NICK_PROMPT,
    OFF,
    ON,
    PROMPT_Y,
    RESPONSE_WINDOW,
    REST_INTERVAL,
    SETTINGS_SCREEN,
    SIM_INTRO_KEYS,
    SIM_WINDOW_MODE,
    TEXT_COLOR,
    TEXT_HEIGHT,
    TEXT_WRAP_SHARE,
    WARNING_COLOR,
    WINDOW_MODE,
    WINDOW_MODES,
)
from logic import (
    NickInput,
    SimulatedKeyboard,
    SimulatedKeyPress,
    Start,
    apply_settings_key,
    assign_block_order,
    classify_press,
    companion_path,
    count_completed_sessions,
    finish_meta,
    genuine_presses,
    git_commit,
    machine_code,
    make_data_path,
    make_meta,
    make_plan,
    make_row,
    make_sim_scenario,
    nick_exists,
    nick_input_key,
    outcome_without_press,
    parse_args,
    session_data_dir,
    settings_order_note,
    sim_window_size,
    write_meta,
)

logging.console.setLevel(logging.ERROR)

import pyglet  # noqa: E402
from psychopy import core, visual  # noqa: E402
from psychopy.hardware import keyboard  # noqa: E402

# Program čte klávesy buď ze skutečné klávesnice (iohub), nebo ze simulace se stejným rozhraním.
AnyKeyboard = keyboard.Keyboard | SimulatedKeyboard
AnyKeyPress = keyboard.KeyPress | SimulatedKeyPress


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
) -> None:
    """Vykreslení pauzy mezi jednotlivými starty."""
    for _ in range(frames(rest_time, rate)):
        quit_if_escape(kb.getKeys(keyList=["escape"], waitRelease=False), win)
        draw_lamps(lamps, 0)
        win.flip()


def quit_if_escape(keys: list[AnyKeyPress], win: visual.Window) -> None:
    """Ukončí program v libovolné chvíli při stisku esc."""
    if any(key.name == "escape" for key in keys):
        win.close()
        core.quit()


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


def make_text(
    win: visual.Window, y: int = 0, color: str = TEXT_COLOR
) -> visual.TextStim:
    """Vytvoří prázdný text pro obrazovky s textem, zalomený podle šířky okna."""
    return visual.TextStim(
        win,
        text="",
        pos=(0, y),
        height=TEXT_HEIGHT,
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


def main() -> None:
    try:
        simulated, escape_at = parse_args(sys.argv[1:])
    except ValueError as error:
        sys.exit(str(error))
    if WINDOW_MODE not in WINDOW_MODES:
        sys.exit(
            f"WINDOW_MODE {WINDOW_MODE!r} není povolený pro ostrý běh: {WINDOW_MODES}"
        )
    window_mode = SIM_WINDOW_MODE if simulated else WINDOW_MODE
    exit_if_hidden_launch(window_mode)
    machine = machine_code(sys.platform)
    project_dir = Path(__file__).parent
    data_root = project_dir / DATA_DIR_NAME

    real_kb = None if simulated else open_keyboard()
    # Bez toho PsychoPy po 5 vypadlých snímcích přestane varovat a log by je nezachytil.
    visual.window.reportNDroppedFrames = DROPPED_FRAME_WARNINGS_MAX
    win = open_window(window_mode)
    logging.console.setLevel(logging.WARNING)
    rate = measure_frame_rate(win)
    window_size = (int(win.size[0]), int(win.size[1]))
    print(
        f"systém {sys.platform}, režim {window_mode}, velikost okna {window_size} px, "
        f"frekvence {rate:.2f} Hz{', SIMULACE' if simulated else ''}",
        flush=True,
    )

    plan = make_plan()
    scenario = make_sim_scenario(plan, escape_at) if simulated else None
    kb = (
        SimulatedKeyboard(scenario, rate, list(SIM_INTRO_KEYS))
        if simulated
        else real_kb
    )

    def exists(nick: str) -> bool:
        """Existuje už sezení s tímto nickem? V simulaci se nekontroluje."""
        return not simulated and nick_exists(
            session_data_dir(data_root, simulated, nick), nick
        )

    nick = ask_nick(win, kb, exists)
    data_dir = session_data_dir(data_root, simulated, nick)
    completed = count_completed_sessions(data_root, machine)
    block_order, language = ask_settings(
        win,
        kb,
        nick,
        machine,
        completed,
        "" if data_dir == data_root else data_dir.name,
    )

    started_at = datetime.now().astimezone()
    data_dir.mkdir(parents=True, exist_ok=True)
    data_path = make_data_path(data_dir, nick, machine, started_at)
    if data_path.exists():
        win.close()
        sys.exit(
            f"Soubor {data_path.name} už existuje (stejný nick ve stejné minutě).\n"
            "Počkej minutu a spusť experiment znovu."
        )
    meta_path = companion_path(data_path, META_SUFFIX)
    log_path = companion_path(data_path, LOG_SUFFIX)
    logging.LogFile(str(log_path), level=logging.WARNING, filemode="w")
    print(f"data: {data_path}, pořadí {block_order}, jazyk {language}", flush=True)

    meta = make_meta(
        participant=nick,
        machine=machine,
        started_at=started_at,
        environment=describe_environment(project_dir),
        frame_rate=float(rate),
        window_mode=window_mode,
        window_size=window_size,
        keyboard_backend=kb.getBackend(),
        planned_starts=len(plan),
        block_order=block_order,
        language=language,
        simulated=simulated,
    )
    if simulated:
        meta = {**meta, "sim_scenario": scenario}
    write_meta(meta_path, meta)

    lamps = make_lamps(win)
    flag = make_flag(win)
    win.recordFrameIntervals = True
    with data_path.open("x", newline="", encoding="utf-8") as data_file:
        writer = csv.DictWriter(data_file, fieldnames=CSV_COLUMNS)
        writer.writeheader()
        for trial_index, start in enumerate(plan, start=1):
            dropped_before = win.nDroppedFrames
            outcome, rt = run_start(win, lamps, rate, kb, flag, start)
            dropped = win.nDroppedFrames - dropped_before
            row = make_row(
                participant=nick,
                machine=machine,
                start=start,
                trial_index=trial_index,
                outcome=outcome,
                rt=rt,
                dropped_frames=dropped,
                written_at=datetime.now().astimezone(),
            )
            writer.writerow(row)
            data_file.flush()
            logging.flush()
            print(
                trial_index,
                start.foreperiod,
                start.is_nogo,
                outcome,
                row["rt_ms"],
                f"vypadlé snímky: {dropped}",
            )
            show_pause(win, lamps, REST_INTERVAL, rate, kb)

    meta = finish_meta(meta, datetime.now().astimezone(), win.nDroppedFrames)
    write_meta(meta_path, meta)
    print(f"Sezení dokončeno, vypadlé snímky celkem: {win.nDroppedFrames}", flush=True)
    win.close()
    core.quit()


if __name__ == "__main__":
    main()
