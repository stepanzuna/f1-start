import csv
import os
import platform
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import TextIO

import psychopy
from psychopy import logging

from config import (
    CSV_COLUMNS,
    DATA_DIR_NAME,
    DIGITS_HEIGHT,
    DROPPED_FRAME_WARNINGS_MAX,
    EXPECTED_FRAME_RATE,
    FEEDBACK_HEIGHT,
    FEEDBACK_Y,
    FLAG_COLOR,
    FLAG_HEIGHT,
    FLAG_POS,
    FLAG_WIDTH,
    FRAME_RATE_TOLERANCE,
    INPUT_Y,
    KEYBOARD_BACKEND,
    LAMP_RADIUS,
    LAMP_SPACING,
    LAMP_Y,
    LIGHT_INTERVAL,
    LOG_SUFFIX,
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
    SIM_SCREENS_SUFFIX,
    SIM_WINDOW_MODE,
    START_KEY,
    TEST_PREFIX,
    TEXTS,
    WINDOW_MODE,
    WINDOW_MODES,
)
from logic import (
    Start,
    assign_block_order,
    build_practice,
    build_session,
    classify_press,
    companion_path,
    count_completed_sessions,
    feedback_text,
    finish_meta,
    git_commit,
    group_sets,
    machine_code,
    make_data_path,
    make_meta,
    make_row,
    make_seed,
    nick_exists,
    outcome_without_press,
    parse_args,
    recall_feedback_text,
    session_data_dir,
    short_plan_allowed,
    write_meta,
)
from simulation import (
    SimulatedKeyboard,
    make_sim_scenario,
    make_sim_typed_keys,
    sim_sequence,
    sim_window_size,
)

logging.console.setLevel(logging.ERROR)

import pyglet  # noqa: E402
from psychopy import core, visual  # noqa: E402
from psychopy.hardware import keyboard  # noqa: E402

from screens import (  # noqa: E402
    AnyKeyboard,
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
)


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


def capture_once(session: Session, name: str) -> Path | None:
    """Cesta pro obrázek obrazovky, jen v simulaci a jen poprvé pro dané jméno."""
    if session.screens_dir is None or name in session.captured:
        return None
    session.captured.add(name)
    return session.screens_dir / f"{session.trial_index:03d}_{name}.png"


def ask_key(session: Session, text_key: str, keys: tuple[str, ...]) -> str:
    """Text pro účastníka (ve zvoleném jazyce), čeká na jednu z kláves a vrátí ji.

    Klávesy se čtou až po vykreslení prvního snímku, bez keyList (viz CLAUDE.md).
    """
    set_text(session.message, TEXTS[session.language][text_key])
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


def run_sets(
    session: Session,
    plan: list[Start],
    set_digits: dict[tuple[int, int], str],
    practice: bool,
) -> None:
    """Projde sady plánu: číslice, starty se zpětnou vazbou, vybavení, zápis CSV po sadě.

    V testovacím kole (practice) po vybavení ukáže, jestli bylo správně.
    """
    for starts in group_sets(plan):
        digits = set_digits[(starts[0].block, starts[0].set_index)]
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
            session.writer.writerow(
                make_row(
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
            )
        session.data_file.flush()
        logging.flush()


def main() -> None:
    try:
        options = parse_args(sys.argv[1:])
    except ValueError as error:
        sys.exit(str(error))
    simulated = options.simulated
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

    seed = make_seed() if options.seed is None else options.seed
    completed = count_completed_sessions(data_root, machine)
    scenario = None
    kb = real_kb
    if simulated:
        # Simulace pořadí bloků nemění, takže plán i číslice zná předem (stejný seed).
        sim_starts, practice_digits, main_digits = sim_sequence(
            assign_block_order(completed), seed, options.short
        )
        scenario = make_sim_scenario(sim_starts, options.escape_at)
        kb = SimulatedKeyboard(
            scenario, rate, make_sim_typed_keys(practice_digits, main_digits)
        )

    def exists(nick: str) -> bool:
        """Existuje už sezení s tímto nickem? V simulaci se nekontroluje."""
        return not simulated and nick_exists(
            session_data_dir(data_root, simulated, nick), nick
        )

    nick = ask_nick(win, kb, exists)
    if options.short and not short_plan_allowed(simulated, nick):
        win.close()
        sys.exit(
            f"Zkrácený plán (--short) je jen pro testy: nick musí začínat "
            f"{TEST_PREFIX!r}, nebo spusť simulaci. Nick {nick!r} by šel mezi ostrá data."
        )
    data_dir = session_data_dir(data_root, simulated, nick)
    block_order, language = ask_settings(
        win,
        kb,
        nick,
        machine,
        completed,
        "" if data_dir == data_root else data_dir.name,
    )

    plan, set_digits = build_session(block_order, seed, options.short)
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
    print(
        f"data: {data_path}, pořadí {block_order}, jazyk {language}, seed {seed}, "
        f"startů {len(plan)}{' (zkrácený plán)' if options.short else ''}",
        flush=True,
    )

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
        seed=seed,
        short=options.short,
        simulated=simulated,
    )
    if simulated:
        meta = {**meta, "sim_scenario": scenario}
    write_meta(meta_path, meta)

    screens_dir = data_dir / (data_path.stem + SIM_SCREENS_SUFFIX)
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
            language=language,
            nick=nick,
            machine=machine,
            writer=writer,
            data_file=data_file,
            lamps=make_lamps(win),
            flag=make_flag(win),
            feedback=make_text(win, FEEDBACK_Y, height=FEEDBACK_HEIGHT),
            message=make_text(win),
            digits_stim=make_text(win, height=DIGITS_HEIGHT),
            prompt=make_text(win, PROMPT_Y),
            typed=make_text(win, INPUT_Y, height=DIGITS_HEIGHT),
            screens_dir=screens_dir if simulated else None,
        )
        practice_rounds = 0
        repeat = True
        while repeat:
            practice_rounds += 1
            starts, digits = build_practice(seed, practice_rounds)[-1]
            print(f"testovací kolo {practice_rounds}", flush=True)
            ask_key(session, "practice_start", (START_KEY,))
            run_sets(session, starts, digits, practice=True)
            choice = ask_key(
                session, "practice_end", (PRACTICE_REPEAT_KEY, PRACTICE_CONTINUE_KEY)
            )
            repeat = choice == PRACTICE_REPEAT_KEY
        run_sets(session, plan, set_digits, practice=False)

    meta = finish_meta(
        meta, datetime.now().astimezone(), win.nDroppedFrames, practice_rounds
    )
    write_meta(meta_path, meta)
    print(f"Sezení dokončeno, vypadlé snímky celkem: {win.nDroppedFrames}", flush=True)
    win.close()
    core.quit()


if __name__ == "__main__":
    main()
