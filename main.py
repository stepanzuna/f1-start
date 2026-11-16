import csv
import sys
from dataclasses import dataclass, replace
from datetime import datetime
from pathlib import Path

from psychopy import logging

from config import (
    CSV_COLUMNS,
    DATA_DIR_NAME,
    DEFAULT_LANGUAGE,
    DIGITS_HEIGHT,
    DROPPED_FRAME_WARNINGS_MAX,
    END_KEY,
    ENTER_KEYS,
    FEEDBACK_HEIGHT,
    FEEDBACK_Y,
    INPUT_Y,
    LOG_SUFFIX,
    MACHINE_FILE_NAME,
    META_SUFFIX,
    N_LAMPS,
    PROMPT_Y,
    SETTINGS_CALIBRATE,
    SETTINGS_START,
    SIM_SCREENS_SUFFIX,
    SIM_WINDOW_MODE,
    SIZE_CHECK_TEXT_Y,
    TEST_PREFIX,
    WINDOW_MODE,
    WINDOW_MODES,
    WINDOWS_DPI_AWARENESS,
)
from logic import (
    Calibration,
    MachineInfo,
    RunOptions,
    SettingsInfo,
    assign_block_order,
    build_session,
    calibration_for_window,
    companion_path,
    count_completed_sessions,
    finish_meta,
    load_machine_info,
    machine_code,
    make_data_path,
    make_meta,
    make_seed,
    nick_exists,
    parse_args,
    provisional_px_per_cm,
    recalibrated,
    save_machine_info,
    session_data_dir,
    session_summary,
    short_plan_allowed,
    size_check_text,
    write_json,
)
from simulation import (
    SimulatedKeyboard,
    make_sim_scenario,
    make_sim_typed_keys,
    sim_machine_info,
    sim_sequence,
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

from psychopy import core, visual  # noqa: E402

from display import (  # noqa: E402
    describe_environment,
    exit_if_hidden_launch,
    open_display,
    open_keyboard,
)
from screens import (  # noqa: E402
    AnyKeyboard,
    ask_calibration,
    ask_nick,
    ask_settings,
    make_text,
    read_screen_keys,
    set_text,
    window_size_pix,
)
from session import (  # noqa: E402
    Session,
    ask_key,
    run_main,
    run_practice,
    show_instructions,
)
from trial import (  # noqa: E402
    draw_lamps,
    make_flag,
    make_lamps,
)


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
