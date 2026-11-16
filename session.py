"""Průběh sezení (PsychoPy): sady, testovací kolo, instrukce, Paasova škála a bloky.

Přesunuto z main.py beze změny kódu (refaktorizace 16. 11. 2026). Importuje se až po zapnutí
DPI awareness a ztišení logování v main.py (viz CLAUDE.md, Logování).
"""

import csv
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import TextIO

from psychopy import logging, visual

from config import (
    DIGITS_HEIGHT,
    ENTER_KEYS,
    FEEDBACK_HEIGHT,
    FEEDBACK_Y,
    INPUT_Y,
    INSTRUCTION_SCREENS,
    PRACTICE_CONTINUE_KEY,
    PRACTICE_REPEAT_KEY,
    PROMPT_Y,
    RECALL_FEEDBACK_DURATION,
    REST_INTERVAL,
    START_KEY,
    TEXTS,
)
from logic import (
    Start,
    build_practice,
    effort_rating,
    feedback_text,
    group_sets,
    make_row,
    recall_feedback_text,
    split_blocks,
    write_json,
)
from screens import (
    AnyKeyboard,
    ask_recall,
    make_text,
    read_screen_keys,
    save_frame,
    set_text,
    show_digits,
    show_message,
)
from trial import make_flag, make_lamps, run_start, show_pause


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


def make_session(
    win: visual.Window,
    kb: AnyKeyboard,
    rate: float,
    px_per_cm: float,
    language: str,
    nick: str,
    machine: str,
    writer: csv.DictWriter,
    data_file: TextIO,
    screens_dir: Path | None,
) -> Session:
    """Sezení s podněty v kalibrované velikosti (lampy, vlajka, texty) a otevřeným CSV."""
    return Session(
        win=win,
        kb=kb,
        rate=rate,
        language=language,
        nick=nick,
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
        screens_dir=screens_dir,
    )


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


# Výsledek jednoho startu do zápisu: pořadí v sezení, start, výsledek, RT, vypadlé snímky
StartResult = tuple[int, Start, str, float | None, int]


def run_counted_start(session: Session, start: Start) -> StartResult:
    """Jeden start s počítáním vypadlých snímků, výpisem do terminálu a pauzou se zpětnou vazbou."""
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
    return (session.trial_index, start, outcome, rt, dropped)


def ask_set_recall(session: Session, digits: str, practice: bool) -> str:
    """Vybavení číslic sady; v testovacím kole (practice) i hláška, jestli bylo správně."""
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
    return typed


def write_set(
    session: Session, results: list[StartResult], digits: str, typed: str
) -> None:
    """Zápis sady do CSV po vybavení (docs/experiment.md, Data) a hned na disk.

    Část 1 testovacího kola (bez číslic) se tak zapisuje po každém startu.
    """
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
    results = [run_counted_start(session, start) for start in starts]
    typed = ask_set_recall(session, digits, practice) if digits else ""
    write_set(session, results, digits, typed)


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
