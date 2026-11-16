import csv
import sys
from dataclasses import dataclass, replace
from datetime import datetime
from pathlib import Path

from psychopy import logging

from config import (
    CSV_COLUMNS,
    DATA_DIR_NAME,
    DROPPED_FRAME_WARNINGS_MAX,
    END_KEY,
    LOG_SUFFIX,
    MACHINE_FILE_NAME,
    META_SUFFIX,
    SIM_SCREENS_SUFFIX,
    SIM_WINDOW_MODE,
    WINDOW_MODE,
    WINDOW_MODES,
    WINDOWS_DPI_AWARENESS,
)
from logic import (
    MachineInfo,
    RunOptions,
    SettingsInfo,
    Start,
    assign_block_order,
    build_session,
    companion_path,
    count_completed_sessions,
    finish_meta,
    load_machine_info,
    machine_code,
    make_meta,
    make_seed,
    parse_args,
    save_machine_info,
    session_summary,
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
    Display,
    describe_environment,
    exit_if_hidden_launch,
    open_display,
    open_keyboard,
)
from intro import (  # noqa: E402
    Participant,
    ask_participant,
    create_data_path,
    ensure_calibration,
)
from screens import AnyKeyboard  # noqa: E402
from session import (  # noqa: E402
    Session,
    ask_key,
    make_session,
    run_main,
    run_practice,
    show_instructions,
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
class Startup:
    """Co je připravené před úvodními obrazovkami: okno, klávesnice, seed a počítač."""

    options: RunOptions
    display: Display
    kb: AnyKeyboard
    scenario: list[str] | None  # jen simulace: typ odpovědi pro každý start
    seed: int
    machine: str
    completed: int  # dokončená ostrá sezení na tomto počítači (střídání pořadí bloků)
    machine_info: MachineInfo
    data_root: Path


def start_up(options: RunOptions, data_root: Path) -> Startup:
    """Klávesnice, okno a frekvence, seed, počet dokončených sezení a údaje o počítači.

    Klávesnice iohub se spouští před oknem; simulace ji nahradí falešnou klávesnicí.
    """
    simulated = options.simulated
    machine = machine_code(sys.platform)
    real_kb = None if simulated else open_keyboard()
    # Bez toho PsychoPy po 5 vypadlých snímcích přestane varovat a log by je nezachytil.
    visual.window.reportNDroppedFrames = DROPPED_FRAME_WARNINGS_MAX
    display = open_display(simulated)
    seed = make_seed() if options.seed is None else options.seed
    completed = count_completed_sessions(data_root, machine)
    scenario = None
    kb = real_kb
    if simulated:
        kb, scenario = make_sim_keyboard(options, seed, completed, display.rate)
    machine_info = (
        sim_machine_info(display.size)
        if simulated
        else load_machine_info(data_root / MACHINE_FILE_NAME)
    )
    return Startup(
        options,
        display,
        kb,
        scenario,
        seed,
        machine,
        completed,
        machine_info,
        data_root,
    )


def ask_intro(startup: Startup) -> Participant:
    """Úvodní obrazovky: kalibrace (jen když pro okno chybí), nick a nastavení."""
    display = startup.display
    info = SettingsInfo(
        nick="",
        machine=startup.machine,
        machine_id=startup.machine_info.machine_id,
        folder="",
        completed=startup.completed,
        calibration=ensure_calibration(
            display.win, startup.kb, startup.machine_info, display.size
        ),
    )
    return ask_participant(
        display.win, startup.kb, startup.options, startup.data_root, info
    )


def open_session_files(
    startup: Startup, participant: Participant, planned_starts: int, project_dir: Path
) -> tuple[Path, Path, dict[str, object]]:
    """Založí soubory sezení: cesta k CSV, data/machine.json, log a meta s aborted = true.

    Vrátí (cesta k CSV, cesta k meta, meta).
    """
    options, display = startup.options, startup.display
    started_at = datetime.now().astimezone()
    data_path = create_data_path(display.win, participant, startup.machine, started_at)
    if not options.simulated:  # simulace soubor počítače nečte ani nemění
        save_machine_info(
            startup.data_root / MACHINE_FILE_NAME,
            replace(startup.machine_info, calibration=participant.calibration),
        )
    meta_path = companion_path(data_path, META_SUFFIX)
    log_path = companion_path(data_path, LOG_SUFFIX)
    logging.LogFile(str(log_path), level=logging.WARNING, filemode="w")
    print(
        f"data: {data_path}, pořadí {participant.block_order}, "
        f"jazyk {participant.language}, seed {startup.seed}, "
        f"startů {planned_starts}{' (zkrácený plán)' if options.short else ''}",
        flush=True,
    )
    meta = make_meta(
        participant=participant.nick,
        machine=startup.machine,
        started_at=started_at,
        environment=describe_environment(project_dir),
        frame_rate=float(display.rate),
        window_mode=display.mode,
        window_size=display.size,
        keyboard_backend=startup.kb.getBackend(),
        planned_starts=planned_starts,
        block_order=participant.block_order,
        language=participant.language,
        seed=startup.seed,
        short=options.short,
        simulated=options.simulated,
        machine_id=startup.machine_info.machine_id,
        calibration=participant.calibration,
        dpi_aware=DPI_AWARE,
    )
    if options.simulated:
        meta = {**meta, "sim_scenario": startup.scenario}
    write_json(meta_path, meta)
    return data_path, meta_path, meta


def run_session(
    startup: Startup,
    participant: Participant,
    data_path: Path,
    meta: dict[str, object],
    meta_path: Path,
    plan: list[Start],
    set_digits: dict[tuple[int, int], str],
) -> tuple[Session, dict[str, object], int]:
    """Instrukce, testovací kola a ostrá část; CSV je otevřené po celou dobu.

    Vrátí (sezení, meta s hodnoceními úsilí, počet testovacích kol).
    """
    win, simulated = startup.display.win, startup.options.simulated
    screens_dir = participant.data_dir / (data_path.stem + SIM_SCREENS_SUFFIX)
    if simulated:
        screens_dir.mkdir()
    win.recordFrameIntervals = True
    with data_path.open("x", newline="", encoding="utf-8") as data_file:
        writer = csv.DictWriter(data_file, fieldnames=CSV_COLUMNS)
        writer.writeheader()
        data_file.flush()  # hlavička hned na disk, i kdyby první sada nedoběhla
        session = make_session(
            win=win,
            kb=startup.kb,
            rate=startup.display.rate,
            px_per_cm=participant.calibration.px_per_cm,
            language=participant.language,
            nick=participant.nick,
            machine=startup.machine,
            writer=writer,
            data_file=data_file,
            screens_dir=screens_dir if simulated else None,
        )
        show_instructions(session)
        practice_rounds = run_practice(session, startup.seed)
        meta = run_main(session, plan, set_digits, meta, meta_path)
    return session, meta, practice_rounds


def finish_session(
    session: Session, meta: dict[str, object], meta_path: Path, practice_rounds: int
) -> None:
    """Meta jako řádně dokončené sezení, pak zhodnocení pro účastníka (zavírá Escape)."""
    win = session.win
    meta = finish_meta(
        meta, datetime.now().astimezone(), win.nDroppedFrames, practice_rounds
    )
    write_json(meta_path, meta)
    print(f"Sezení dokončeno, vypadlé snímky celkem: {win.nDroppedFrames}", flush=True)
    # Zhodnocení až po uložení všech dat, takže měření neovlivní.
    ask_key(session, "end", (END_KEY,), **session_summary(session.rows))
    win.close()
    core.quit()


def main() -> None:
    """Sezení po fázích: příprava, úvod, soubory, průběh, konec."""
    options = read_options()
    project_dir = Path(__file__).parent
    startup = start_up(options, project_dir / DATA_DIR_NAME)
    participant = ask_intro(startup)
    plan, set_digits = build_session(
        participant.block_order, startup.seed, options.short
    )
    data_path, meta_path, meta = open_session_files(
        startup, participant, len(plan), project_dir
    )
    session, meta, practice_rounds = run_session(
        startup, participant, data_path, meta, meta_path, plan, set_digits
    )
    finish_session(session, meta, meta_path, practice_rounds)


if __name__ == "__main__":
    main()
