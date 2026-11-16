import csv
import os
import platform
import sys
from dataclasses import dataclass, field, replace
from datetime import datetime
from pathlib import Path
from typing import TextIO

import psychopy
from psychopy import logging

from config import (
    CSV_COLUMNS,
    DATA_DIR_NAME,
    DEFAULT_LANGUAGE,
    DIGITS_HEIGHT,
    DROPPED_FRAME_WARNINGS_MAX,
    END_KEY,
    ENTER_KEYS,
    EXPECTED_FRAME_RATE,
    FEEDBACK_HEIGHT,
    FEEDBACK_Y,
    FLAG_COLOR,
    FLAG_HEIGHT,
    FLAG_POS,
    FLAG_WIDTH,
    FRAME_RATE_TOLERANCE,
    INPUT_Y,
    INSTRUCTION_SCREENS,
    KEYBOARD_BACKEND,
    LAMP_RADIUS,
    LAMP_SPACING,
    LAMP_Y,
    LIGHT_INTERVAL,
    LOG_SUFFIX,
    MACHINE_FILE_NAME,
    META_SUFFIX,
    N_LAMPS,
    OFF,
    ON,
    PRACTICE_CONTINUE_KEY,
    PRACTICE_REPEAT_KEY,
    PROMPT_Y,
    RECALL_FEEDBACK_DURATION,
    RESPONSE_WINDOW,
    REST_INTERVAL,
    SETTINGS_CALIBRATE,
    SETTINGS_START,
    SIM_SCREENS_SUFFIX,
    SIM_WINDOW_MODE,
    SIZE_CHECK_TEXT_Y,
    START_KEY,
    TEST_PREFIX,
    TEXTS,
    WINDOW_MODE,
    WINDOW_MODES,
    WINDOWS_DPI_AWARENESS,
)
from logic import (
    Calibration,
    MachineInfo,
    RunOptions,
    SettingsInfo,
    Start,
    assign_block_order,
    build_practice,
    build_session,
    calibration_for_window,
    classify_press,
    companion_path,
    count_completed_sessions,
    effort_rating,
    feedback_text,
    finish_meta,
    git_commit,
    group_sets,
    load_machine_info,
    machine_code,
    make_data_path,
    make_meta,
    make_row,
    make_seed,
    nick_exists,
    outcome_without_press,
    parse_args,
    provisional_px_per_cm,
    recalibrated,
    recall_feedback_text,
    save_machine_info,
    session_data_dir,
    session_summary,
    short_plan_allowed,
    size_check_text,
    split_blocks,
    write_json,
)
from simulation import (
    SimulatedKeyboard,
    make_sim_scenario,
    make_sim_typed_keys,
    sim_machine_info,
    sim_sequence,
    sim_window_size,
)


def enable_dpi_awareness() -> bool | None:
    """Windows: okno v nativních pixelech displeje, bez roztažení podle měřítka (125 % apod.).

    Musí proběhnout před prvním oknem: PsychoPy ho vytvoří (skryté okno pygletu) už
    při importu psychopy.visual, proto se volá na úrovni modulu před tímto importem.
    Vrátí, jestli je proces DPI aware (do meta); mimo Windows None.
    """
    if sys.platform != "win32":
        return None
    import ctypes

    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(WINDOWS_DPI_AWARENESS)
    except (AttributeError, OSError):
        ctypes.windll.user32.SetProcessDPIAware()  # starší Windows bez shcore
    return bool(ctypes.windll.user32.IsProcessDPIAware())


logging.console.setLevel(logging.ERROR)
# Spočítá se jednou při startu (před importem visual níže), dál se jen čte jako konstanta.
DPI_AWARE = enable_dpi_awareness()

import pyglet  # noqa: E402
from psychopy import core, visual  # noqa: E402
from psychopy.hardware import keyboard  # noqa: E402

from screens import (  # noqa: E402
    AnyKeyboard,
    ask_calibration,
    ask_nick,
    ask_recall,
    ask_settings,
    frames,
    make_text,
    quit_if_escape,
    read_screen_keys,
    save_frame,
    set_text,
    show_digits,
    show_message,
    window_size_pix,
)


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
class Session:
    """Co potřebuje průběh sad: okno, klávesnice, podněty, jazyk a zápis dat."""

    win: visual.Window
    kb: AnyKeyboard
    rate: float
    language: str
    nick: str
    machine: str
    writer: csv.DictWriter
    data_file: TextIO
    lamps: list[visual.Circle]
    flag: visual.Rect
    feedback: visual.TextStim
    message: visual.TextStim
    digits_stim: visual.TextStim
    prompt: visual.TextStim
    typed: visual.TextStim
    screens_dir: Path | None  # jen simulace: kam uložit obrázky obrazovek
    captured: set[str] = field(default_factory=set)
    trial_index: int = 0
    rows: list[dict[str, object]] = field(
        default_factory=list
    )  # pro závěrečné zhodnocení


def capture_once(session: Session, name: str) -> Path | None:
    """Cesta pro obrázek obrazovky, jen v simulaci a jen poprvé pro dané jméno."""
    if session.screens_dir is None or name in session.captured:
        return None
    session.captured.add(name)
    return session.screens_dir / f"{session.trial_index:03d}_{name}.png"


def ask_key(
    session: Session, text_key: str, keys: tuple[str, ...], **fields: object
) -> str:
    """Text pro účastníka (ve zvoleném jazyce), čeká na jednu z kláves a vrátí ji.

    fields se dosadí do textu ({next_block} apod.). Klávesy se čtou až po vykreslení
    prvního snímku, bez keyList (viz CLAUDE.md).
    """
    set_text(session.message, TEXTS[session.language][text_key].format(**fields))
    capture_path = capture_once(session, text_key)
    session.kb.clearEvents()
    while True:
        session.message.draw()
        if capture_path is not None:
            save_frame(session.win, capture_path)
            capture_path = None
        session.win.flip()
        for key in read_screen_keys(session.win, session.kb):
            if key.name in keys:
                return key.name


def run_set(session: Session, starts: list[Start], digits: str, practice: bool) -> None:
    """Jedna sada: číslice, starty se zpětnou vazbou, vybavení, zápis CSV po sadě.

    V testovacím kole (practice) po vybavení ukáže, jestli bylo správně.
    """
    if digits:
        show_digits(
            session.win,
            session.kb,
            session.digits_stim,
            digits,
            session.rate,
            capture_path=capture_once(session, "digits"),
        )
    results = []
    for start in starts:
        session.trial_index += 1
        dropped_before = session.win.nDroppedFrames
        outcome, rt = run_start(
            session.win,
            session.lamps,
            session.rate,
            session.kb,
            session.flag,
            start,
        )
        dropped = session.win.nDroppedFrames - dropped_before
        results.append((session.trial_index, start, outcome, rt, dropped))
        print(
            session.trial_index,
            start.block,
            start.load,
            start.foreperiod,
            start.is_nogo,
            outcome,
            None if rt is None else round(rt * 1000, 1),
            f"vypadlé snímky: {dropped}",
        )
        show_pause(
            session.win,
            session.lamps,
            REST_INTERVAL,
            session.rate,
            session.kb,
            session.feedback,
            feedback_text(outcome, rt, session.language),
            capture_path=capture_once(session, outcome),
        )
    typed = ""
    if digits:
        typed = ask_recall(
            session.win,
            session.kb,
            session.prompt,
            session.typed,
            TEXTS[session.language]["recall_prompt"],
            len(digits),
            capture_path=capture_once(session, "recall"),
        )
        print(f"číslice {digits}, odpověď {typed}", flush=True)
        if practice:
            show_message(
                session.win,
                session.kb,
                session.message,
                recall_feedback_text(digits, typed, session.language),
                RECALL_FEEDBACK_DURATION,
                session.rate,
                capture_path=capture_once(session, "recall_feedback"),
            )
    # Zápis po sadě (docs/experiment.md, Data); část 1 testovacího kola po startu.
    for index, start, outcome, rt, dropped in results:
        row = make_row(
            participant=session.nick,
            machine=session.machine,
            start=start,
            trial_index=index,
            outcome=outcome,
            rt=rt,
            dropped_frames=dropped,
            written_at=datetime.now().astimezone(),
            digits_shown=digits,
            digits_typed=typed,
        )
        session.writer.writerow(row)
        session.rows.append(row)
    session.data_file.flush()
    logging.flush()


def run_sets(
    session: Session,
    plan: list[Start],
    set_digits: dict[tuple[int, int], str],
    practice: bool,
) -> None:
    """Projde všechny sady plánu po sobě."""
    for starts in group_sets(plan):
        digits = set_digits[(starts[0].block, starts[0].set_index)]
        run_set(session, starts, digits, practice)


def run_practice(session: Session, seed: int) -> int:
    """Testovací kola s úvodní obrazovkou, dokud účastník nezvolí pokračovat; vrátí počet kol."""
    practice_rounds = 0
    repeat = True
    while repeat:
        practice_rounds += 1
        starts, digits = build_practice(seed, practice_rounds)[-1]
        print(f"testovací kolo {practice_rounds}", flush=True)
        ask_key(session, "practice_start", (START_KEY,))
        without_digits = [s for s in starts if not digits[(s.block, s.set_index)]]
        with_digits = [s for s in starts if digits[(s.block, s.set_index)]]
        run_sets(session, without_digits, digits, practice=True)
        ask_key(session, "practice_set_intro", (START_KEY,))
        run_sets(session, with_digits, digits, practice=True)
        choice = ask_key(
            session, "practice_end", (PRACTICE_REPEAT_KEY, PRACTICE_CONTINUE_KEY)
        )
        repeat = choice == PRACTICE_REPEAT_KEY
    return practice_rounds


def show_instructions(session: Session) -> None:
    """Úvodní instrukce pro účastníka, obrazovka po obrazovce (mezerník = dál)."""
    for text_key in INSTRUCTION_SCREENS:
        ask_key(session, text_key, (START_KEY,))


def ask_effort(session: Session) -> int:
    """Paasova škála po bloku: číslo 1–9 se vybere (jde změnit), Enter ho potvrdí.

    Potvrzení Enterem (rozhodnuto 15. 11. 2026) brání tomu, aby se jako hodnocení uložila
    číslice stisknutá omylem hned po vybavení.
    """
    texts = TEXTS[session.language]
    scale = (
        f"{texts['effort_question']}\n\n{texts['effort_low']}\n{texts['effort_mid']}\n"
        f"{texts['effort_high']}\n\n{texts['effort_hint']}"
    )
    selected: int | None = None
    capture_path = capture_once(session, "effort")
    session.kb.clearEvents()
    while True:
        shown = "–" if selected is None else str(selected)
        set_text(
            session.message,
            f"{scale}\n\n{texts['effort_selected'].format(rating=shown)}",
        )
        session.message.draw()
        if capture_path is not None and selected is not None:
            save_frame(session.win, capture_path)
            capture_path = None
        session.win.flip()
        for key in read_screen_keys(session.win, session.kb):
            if key.name in ENTER_KEYS and selected is not None:
                return selected
            selected = effort_rating(key.code or "") or selected


def run_main(
    session: Session,
    plan: list[Start],
    set_digits: dict[tuple[int, int], str],
    meta: dict[str, object],
    meta_path: Path,
) -> dict[str, object]:
    """Ostrá část po blocích: po každém bloku Paasova škála (hned do meta) a pauza.

    Vrátí meta s hodnoceními; přerušené sezení tak má hodnocení dokončených bloků.
    """
    blocks = split_blocks(plan)
    ask_key(session, "main_start", (START_KEY,), n_blocks=len(blocks))
    ratings: list[int] = []
    for number, block in enumerate(blocks, start=1):
        run_sets(session, block, set_digits, practice=False)
        ratings.append(ask_effort(session))
        print(f"blok {number}: hodnocení úsilí {ratings[-1]}", flush=True)
        meta = {**meta, "effort_ratings": list(ratings)}
        write_json(meta_path, meta)
        if number < len(blocks):
            ask_key(
                session,
                "block_pause",
                (START_KEY,),
                next_block=number + 1,
                n_blocks=len(blocks),
            )
    return meta


def read_options() -> RunOptions:
    """Volby z příkazové řádky; neplatné volby, režim okna nebo spuštění z VS Code ukončí program.

    Kontroly jdou před spuštěním klávesnice iohub, aby program skončil hned.
    """
    try:
        options = parse_args(sys.argv[1:])
    except ValueError as error:
        sys.exit(str(error))
    if WINDOW_MODE not in WINDOW_MODES:
        sys.exit(
            f"WINDOW_MODE {WINDOW_MODE!r} není povolený pro ostrý běh: {WINDOW_MODES}"
        )
    exit_if_hidden_launch(SIM_WINDOW_MODE if options.simulated else WINDOW_MODE)
    return options


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


def make_sim_keyboard(
    options: RunOptions, seed: int, completed: int, rate: float
) -> tuple[SimulatedKeyboard, list[str]]:
    """Falešná klávesnice a scénář simulace (pořadí bloků nemění, plán zná předem)."""
    sim_starts, practice_digits, main_digits = sim_sequence(
        assign_block_order(completed), seed, options.short
    )
    scenario = make_sim_scenario(sim_starts, options.escape_at)
    kb = SimulatedKeyboard(
        scenario, rate, make_sim_typed_keys(practice_digits, main_digits)
    )
    return kb, scenario


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


def main() -> None:
    options = read_options()
    simulated = options.simulated
    machine = machine_code(sys.platform)
    project_dir = Path(__file__).parent
    data_root = project_dir / DATA_DIR_NAME

    real_kb = None if simulated else open_keyboard()
    # Bez toho PsychoPy po 5 vypadlých snímcích přestane varovat a log by je nezachytil.
    visual.window.reportNDroppedFrames = DROPPED_FRAME_WARNINGS_MAX
    display = open_display(simulated)
    win, rate = display.win, display.rate

    seed = make_seed() if options.seed is None else options.seed
    completed = count_completed_sessions(data_root, machine)
    scenario = None
    kb = real_kb
    if simulated:
        kb, scenario = make_sim_keyboard(options, seed, completed, rate)

    machine_path = data_root / MACHINE_FILE_NAME
    machine_info = (
        sim_machine_info(display.size) if simulated else load_machine_info(machine_path)
    )
    info = SettingsInfo(
        nick="",
        machine=machine,
        machine_id=machine_info.machine_id,
        folder="",
        completed=completed,
        calibration=ensure_calibration(win, kb, machine_info, display.size),
    )
    participant = ask_participant(win, kb, options, data_root, info)
    px_per_cm = participant.calibration.px_per_cm
    plan, set_digits = build_session(participant.block_order, seed, options.short)
    started_at = datetime.now().astimezone()
    data_path = create_data_path(win, participant, machine, started_at)
    if not simulated:  # simulace soubor počítače nečte ani nemění
        save_machine_info(
            machine_path, replace(machine_info, calibration=participant.calibration)
        )
    meta_path = companion_path(data_path, META_SUFFIX)
    log_path = companion_path(data_path, LOG_SUFFIX)
    logging.LogFile(str(log_path), level=logging.WARNING, filemode="w")
    print(
        f"data: {data_path}, pořadí {participant.block_order}, "
        f"jazyk {participant.language}, seed {seed}, "
        f"startů {len(plan)}{' (zkrácený plán)' if options.short else ''}",
        flush=True,
    )

    meta = make_meta(
        participant=participant.nick,
        machine=machine,
        started_at=started_at,
        environment=describe_environment(project_dir),
        frame_rate=float(rate),
        window_mode=display.mode,
        window_size=display.size,
        keyboard_backend=kb.getBackend(),
        planned_starts=len(plan),
        block_order=participant.block_order,
        language=participant.language,
        seed=seed,
        short=options.short,
        simulated=simulated,
        machine_id=machine_info.machine_id,
        calibration=participant.calibration,
        dpi_aware=DPI_AWARE,
    )
    if simulated:
        meta = {**meta, "sim_scenario": scenario}
    write_json(meta_path, meta)

    screens_dir = participant.data_dir / (data_path.stem + SIM_SCREENS_SUFFIX)
    if simulated:
        screens_dir.mkdir()
    win.recordFrameIntervals = True
    with data_path.open("x", newline="", encoding="utf-8") as data_file:
        writer = csv.DictWriter(data_file, fieldnames=CSV_COLUMNS)
        writer.writeheader()
        data_file.flush()  # hlavička hned na disk, i kdyby první sada nedoběhla
        session = Session(
            win=win,
            kb=kb,
            rate=rate,
            language=participant.language,
            nick=participant.nick,
            machine=machine,
            writer=writer,
            data_file=data_file,
            lamps=make_lamps(win, px_per_cm),
            flag=make_flag(win, px_per_cm),
            feedback=make_text(win, px_per_cm, FEEDBACK_Y, height=FEEDBACK_HEIGHT),
            message=make_text(win, px_per_cm),
            digits_stim=make_text(win, px_per_cm, height=DIGITS_HEIGHT),
            prompt=make_text(win, px_per_cm, PROMPT_Y),
            typed=make_text(win, px_per_cm, INPUT_Y, height=DIGITS_HEIGHT),
            screens_dir=screens_dir if simulated else None,
        )
        show_instructions(session)
        practice_rounds = run_practice(session, seed)
        meta = run_main(session, plan, set_digits, meta, meta_path)

    meta = finish_meta(
        meta, datetime.now().astimezone(), win.nDroppedFrames, practice_rounds
    )
    write_json(meta_path, meta)
    print(f"Sezení dokončeno, vypadlé snímky celkem: {win.nDroppedFrames}", flush=True)
    # Zhodnocení až po uložení všech dat, takže měření neovlivní.
    ask_key(session, "end", (END_KEY,), **session_summary(session.rows))
    win.close()
    core.quit()


if __name__ == "__main__":
    main()
