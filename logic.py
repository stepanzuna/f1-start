"""Čistá logika experimentu bez PsychoPy: start, plán, řádky dat, metadata a simulace."""

import itertools
import json
import random
import secrets
import subprocess
from collections.abc import Callable
from dataclasses import dataclass, replace
from datetime import datetime
from pathlib import Path

from config import (
    ANTICIPATION_THRESHOLD,
    ASSUMED_SCREEN_HEIGHT_CM,
    BACKSPACE_KEY,
    BLOCK_LOADS,
    BLOCK_ORDER_KEYS,
    BLOCK_ORDERS,
    CALIBRATION_ADJUST_FIRST,
    CALIBRATION_INVALID,
    CALIBRATION_KEYS,
    CALIBRATION_NOTE,
    CALIBRATION_NOTE_SIM,
    CALIBRATION_SCREEN,
    CALIBRATION_VALUE,
    CARD_HEIGHT_CM,
    CARD_WIDTH_CM,
    CZECH_DIGIT_ROW,
    DIGITS,
    DIGITS_BLANK,
    DIGITS_DURATION,
    DIGITS_PER_LOAD,
    EFFORT_DIGITS,
    ENTER_KEYS,
    FEEDBACK_KEYS,
    FLAG_HEIGHT,
    FLAG_WIDTH,
    FOLDER_NOTE,
    FOREPERIODS,
    GO_PER_FOREPERIOD,
    LAMP_RADIUS,
    LAMP_SPACING,
    LANGUAGE_KEYS,
    LANGUAGE_NAMES,
    LIGHT_INTERVAL,
    MACHINE_CODES,
    MACHINE_ID_BYTES,
    MACHINE_ID_CHARS,
    MAX_NOGO_RUN,
    MAX_SHUFFLES,
    META_SUFFIX,
    MM_PER_CM,
    NICK_CHARS,
    NICK_EXISTS,
    NICK_INVALID,
    NICK_MAX_LENGTH,
    NICK_MIN_LENGTH,
    NOGO_PER_FOREPERIOD,
    ORDER_AUTO,
    ORDER_MANUAL,
    PILOT_PREFIX,
    PRACTICE_BLOCK,
    PRACTICE_LOAD,
    PRACTICE_SET_NOGO,
    PRACTICE_SINGLE_NOGO,
    PX_PER_CM_DECIMALS,
    PX_PER_CM_MAX,
    PX_PER_CM_MIN,
    RECALL_FEEDBACK_DURATION,
    RESPONSE_WINDOW,
    REST_INTERVAL,
    SEED_FLAG,
    SEED_MAX,
    SETTINGS_ACTIONS,
    SETTINGS_SCREEN,
    SETTINGS_START,
    SHORT_FLAG,
    SHORT_SETS_PER_BLOCK,
    SIM_DIR_NAME,
    SIM_ESCAPE_AT,
    SIM_ESCAPE_FLAG,
    SIM_FLAG,
    SIZE_CHECK_SCREEN,
    STARTS_PER_SET,
    TEST_PREFIX,
    TEXTS,
)


@dataclass
class Start:
    """Jeden start v plánu sezení."""

    foreperiod: float
    is_nogo: bool
    load: str
    block: int
    set_index: int
    start_in_set: int


def make_seed() -> int:
    """Náhodný seed sezení (ukládá se do meta, plán i číslice z něj jdou zopakovat)."""
    return random.SystemRandom().randrange(SEED_MAX)


def split_nogo(rng: random.Random) -> tuple[dict[float, int], dict[float, int]]:
    """Kolik no-go má každá prodleva v prvním a druhém bloku téže podmínky.

    Každá prodleva má v podmínce NOGO_PER_FOREPERIOD no-go (lichý počet, 3), takže je nejde
    rozdělit napůl: polovina prodlev (losuje seed) jich má víc v prvním bloku, zbytek
    ve druhém. Každý blok tak má stejný počet no-go (docs/experiment.md, „Plán startů“).
    """
    more = NOGO_PER_FOREPERIOD - NOGO_PER_FOREPERIOD // 2
    fewer = NOGO_PER_FOREPERIOD // 2
    chosen = set(rng.sample(FOREPERIODS, len(FOREPERIODS) // 2))
    first = {fp: more if fp in chosen else fewer for fp in FOREPERIODS}
    second = {fp: NOGO_PER_FOREPERIOD - first[fp] for fp in FOREPERIODS}
    return first, second


def longest_nogo_run(starts: list[Start]) -> int:
    """Nejdelší řada no-go startů za sebou."""
    longest = current = 0
    for start in starts:
        current = current + 1 if start.is_nogo else 0
        longest = max(longest, current)
    return longest


def make_block(
    load: str, block: int, nogo_per_fp: dict[float, int], rng: random.Random
) -> list[Start]:
    """Jeden blok: každá prodleva stejněkrát, zamíchaný, nejvýš MAX_NOGO_RUN no-go za sebou.

    Míchá se znovu, dokud pravidlo neplatí. Pak se blok rozdělí do sad po STARTS_PER_SET.
    """
    per_fp = (GO_PER_FOREPERIOD + NOGO_PER_FOREPERIOD) // 2
    kinds = [
        (fp, is_nogo)
        for fp in FOREPERIODS
        for is_nogo in [True] * nogo_per_fp[fp] + [False] * (per_fp - nogo_per_fp[fp])
    ]
    for _ in range(MAX_SHUFFLES):
        rng.shuffle(kinds)
        starts = [
            Start(
                foreperiod=fp,
                is_nogo=is_nogo,
                load=load,
                block=block,
                set_index=i // STARTS_PER_SET + 1,
                start_in_set=i % STARTS_PER_SET + 1,
            )
            for i, (fp, is_nogo) in enumerate(kinds)
        ]
        if longest_nogo_run(starts) <= MAX_NOGO_RUN:
            return starts
    raise RuntimeError(
        f"Blok {block} se nepodařilo zamíchat s nejvýš {MAX_NOGO_RUN} no-go za sebou "
        f"ani na {MAX_SHUFFLES} pokusů; zkontroluj počty v config.py."
    )


def make_session_plan(block_order: str, rng: random.Random) -> list[Start]:
    """Plán celého sezení: 4 bloky v pořadí ABBA/BAAB, každá podmínka rozdělená do 2 bloků."""
    splits = {letter: list(split_nogo(rng)) for letter in sorted(set(block_order))}
    plan = []
    for block, letter in enumerate(block_order, start=1):
        nogo_per_fp = splits[letter].pop(0)
        plan += make_block(BLOCK_LOADS[letter], block, nogo_per_fp, rng)
    return plan


def practice_round(
    rng: random.Random,
) -> tuple[list[Start], dict[tuple[int, int], str]]:
    """Jedno testovací kolo: každá prodleva jednou bez číslic, pak sada s nízkou zátěží.

    Část 1 (bez číslic) má sady po jednom startu, aby se zapisovala po každém startu.
    """
    singles = list(FOREPERIODS)
    rng.shuffle(singles)
    single_nogo = set(rng.sample(range(len(singles)), PRACTICE_SINGLE_NOGO))
    starts = [
        Start(fp, i in single_nogo, "none", PRACTICE_BLOCK, i + 1, 1)
        for i, fp in enumerate(singles)
    ]
    set_index = len(singles) + 1
    set_fps = rng.sample(FOREPERIODS, STARTS_PER_SET)
    set_nogo = set(rng.sample(range(STARTS_PER_SET), PRACTICE_SET_NOGO))
    starts += [
        Start(fp, i in set_nogo, PRACTICE_LOAD, PRACTICE_BLOCK, set_index, i + 1)
        for i, fp in enumerate(set_fps)
    ]
    digits = {(PRACTICE_BLOCK, i + 1): "" for i in range(len(singles))}
    digits[(PRACTICE_BLOCK, set_index)] = make_digits(PRACTICE_LOAD, rng)
    return starts, digits


def build_practice(
    seed: int, rounds: int
) -> list[tuple[list[Start], dict[tuple[int, int], str]]]:
    """Testovací kola ze seedu (vlastní generátor, plán ostré části se tím nemění).

    Opakované kolo je nové (jiné prodlevy i číslice), ale ze stejného seedu vždy stejné.
    """
    rng = random.Random(f"practice-{seed}")
    return [practice_round(rng) for _ in range(rounds)]


def recall_feedback_text(shown: str, typed: str, language: str) -> str:
    """Hláška ke správnosti vybavení v testovacím kole."""
    if typed == shown:
        return TEXTS[language]["recall_correct"]
    return TEXTS[language]["recall_wrong"].format(digits=" ".join(shown))


def shorten_plan(plan: list[Start], sets_per_block: int) -> list[Start]:
    """Zkrácený plán pro testy: z každého bloku jen prvních sets_per_block sad."""
    return [start for start in plan if start.set_index <= sets_per_block]


def build_session(
    block_order: str, seed: int, short: bool
) -> tuple[list[Start], dict[tuple[int, int], str]]:
    """Plán a číslice sezení ze seedu: stejný seed a pořadí bloků = stejné sezení.

    Číslice se losují pro celý plán, zkrácení až potom, takže zkrácené sezení má stejné
    číslice jako odpovídající sady plného.
    """
    rng = random.Random(seed)
    plan = make_session_plan(block_order, rng)
    digits = make_set_digits(plan, rng)
    if short:
        plan = shorten_plan(plan, SHORT_SETS_PER_BLOCK)
    return plan, digits


def group_sets(plan: list[Start]) -> list[list[Start]]:
    """Seskupí po sobě jdoucí starty téže sady (stejný blok a pořadí sady)."""
    return [
        list(starts)
        for _, starts in itertools.groupby(plan, key=lambda s: (s.block, s.set_index))
    ]


def set_keys(plan: list[Start]) -> list[tuple[int, int]]:
    """Klíč sady (blok, pořadí sady) pro každý start plánu."""
    return [(start.block, start.set_index) for start in plan]


def make_digits(load: str, rng: random.Random) -> str:
    """Číslice pro sadu: počet podle zátěže, bez opakování, nula smí být první."""
    return "".join(rng.sample(DIGITS, DIGITS_PER_LOAD[load]))


def make_set_digits(
    plan: list[Start], rng: random.Random
) -> dict[tuple[int, int], str]:
    """Číslice pro každou sadu plánu, vygenerované předem (klíč: blok, pořadí sady)."""
    digits: dict[tuple[int, int], str] = {}
    for start in plan:
        key = (start.block, start.set_index)
        if key not in digits:
            digits[key] = make_digits(start.load, rng)
    return digits


def split_blocks(plan: list[Start]) -> list[list[Start]]:
    """Rozdělí plán na bloky (po sobě jdoucí starty se stejným blokem)."""
    return [
        list(starts) for _, starts in itertools.groupby(plan, key=lambda s: s.block)
    ]


def effort_rating(char: str) -> int | None:
    """Hodnocení na Paasově škále z napsaného znaku (i česká horní řada), jinak None."""
    digit = recall_char(char)
    return int(digit) if len(digit) == 1 and digit in EFFORT_DIGITS else None


def session_summary(rows: list[dict[str, object]]) -> dict[str, object]:
    """Zhodnocení ostré části pro závěrečnou obrazovku (řádky z make_row).

    Průměrná reakce z go startů, předčasné starty (jump_start i anticipation), starty pod
    vlajkou z no-go startů a podíl správně vybavených sad podle zátěže (v %).
    """
    main = [row for row in rows if row["block"] != PRACTICE_BLOCK]
    go_rts = [row["rt_ms"] for row in main if row["outcome"] == "go"]
    sets: dict[tuple[object, object], tuple[object, object]] = {}
    for row in main:
        sets[(row["block"], row["set_index"])] = (row["load"], row["recall_correct"])

    def recall_percent(load: str) -> str:
        results = [correct for set_load, correct in sets.values() if set_load == load]
        return str(round(100 * sum(results) / len(results))) if results else "–"

    return {
        "mean_rt": str(round(sum(go_rts) / len(go_rts))) if go_rts else "–",
        "false_starts": sum(
            row["outcome"] in ("jump_start", "anticipation") for row in main
        ),
        "starts": len(main),
        "commissions": sum(row["outcome"] == "commission" for row in main),
        "nogo": sum(bool(row["is_nogo"]) for row in main),
        "recall_low": recall_percent("low"),
        "recall_high": recall_percent("high"),
    }


def recall_char(char: str) -> str:
    """Znak z klávesnice při vybavení: česká horní řada bez Shiftu se bere jako číslice."""
    return CZECH_DIGIT_ROW.get(char.lower(), char)


def edit_recall(text: str, name: str, char: str, n_digits: int) -> str:
    """Upraví psanou odpověď při vybavení: jen číslice, nejvýš tolik, kolik jich bylo."""
    return edit_text(text, name, recall_char(char), DIGITS, n_digits)


def classify_press(rt: float, is_nogo: bool) -> str:
    """Vyhodnotí stisk v okně odpovědi v pořadí podle docs/experiment.md."""
    if rt < 0:
        return "jump_start"
    if is_nogo:
        return "commission"
    if rt < ANTICIPATION_THRESHOLD:
        return "anticipation"
    return "go"


def feedback_text(outcome: str, rt: float | None, language: str) -> str:
    """Hláška do pauzy po startu ve zvoleném jazyce; u go s reakčním časem v celých ms."""
    template = TEXTS[language][FEEDBACK_KEYS[outcome]]
    if outcome == "go":
        return template.format(rt_ms=round(rt * 1000))
    return template


def outcome_without_press(is_nogo: bool) -> str:
    """Výsledek startu, ve kterém do konce okna odpovědi nikdo nestiskl."""
    return "inhibit" if is_nogo else "omission"


def machine_code(platform: str) -> str:
    """Převede `sys.platform` na kód stroje do dat ("mac" nebo "win")."""
    if platform not in MACHINE_CODES:
        raise ValueError(
            f"Nepodporovaný systém {platform!r}, povolené: {MACHINE_CODES}"
        )
    return MACHINE_CODES[platform]


def make_data_path(
    data_dir: Path, nick: str, machine: str, started_at: datetime
) -> Path:
    """Sestaví cestu k CSV ve tvaru {nick}_{stroj}_{YYYY-MM-DD_HHMM}.csv."""
    return data_dir / f"{nick}_{machine}_{started_at:%Y-%m-%d_%H%M}.csv"


def make_row(
    participant: str,
    machine: str,
    start: Start,
    trial_index: int,
    outcome: str,
    rt: float | None,
    dropped_frames: int,
    written_at: datetime,
    digits_shown: str = "",
    digits_typed: str = "",
) -> dict[str, object]:
    """Sestaví jeden řádek CSV (jeden start) ve sloupcích podle CSV_COLUMNS.

    Bez číslic (zátěž "none") zůstanou sloupce číslic prázdné.
    """
    return {
        "participant": participant,
        "machine": machine,
        "phase": "practice" if start.block == PRACTICE_BLOCK else "main",
        "block": start.block,
        "load": start.load,
        "set_index": start.set_index,
        "start_in_set": start.start_in_set,
        "trial_index": trial_index,
        "foreperiod_s": start.foreperiod,
        "is_nogo": start.is_nogo,
        "outcome": outcome,
        "rt_ms": "" if rt is None else round(rt * 1000, 1),
        "digits_shown": digits_shown,
        "digits_typed": digits_typed if digits_shown else "",
        "recall_correct": (digits_typed == digits_shown) if digits_shown else "",
        "dropped_frames": dropped_frames,
        "timestamp": written_at.isoformat(timespec="seconds"),
    }


def companion_path(csv_path: Path, suffix: str) -> Path:
    """Odvodí z cesty k CSV cestu k souboru téhož sezení (meta, log)."""
    return csv_path.with_name(csv_path.stem + suffix)


def git_commit(repo_dir: Path) -> str:
    """Vrátí krátký hash commitu, s příponou -dirty při necommitnutých změnách.

    Počítají se i nové nesledované soubory (data/ je v .gitignore, nepočítá se).
    """
    try:
        head = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=repo_dir,
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()
        changes = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=repo_dir,
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return "unknown"
    return f"{head}-dirty" if changes else head


@dataclass(frozen=True)
class Calibration:
    """Kalibrace velikosti: pixely na centimetr pro danou velikost okna.

    calibrated_at je čas kalibrace (ISO 8601), None = pevná hodnota simulace.
    """

    px_per_cm: float
    window_size: tuple[int, int]
    calibrated_at: str | None


@dataclass(frozen=True)
class MachineInfo:
    """Údaje o tomto počítači (data/machine.json): anonymní identifikátor a kalibrace."""

    machine_id: str
    calibration: Calibration | None = None


def make_meta(
    participant: str,
    machine: str,
    started_at: datetime,
    environment: dict[str, str],
    frame_rate: float,
    window_mode: str,
    window_size: tuple[int, int],
    keyboard_backend: str,
    planned_starts: int,
    block_order: str,
    language: str,
    seed: int,
    short: bool,
    simulated: bool,
    machine_id: str,
    calibration: Calibration,
    dpi_aware: bool | None,
) -> dict[str, object]:
    """Sestaví metadata sezení; dokud sezení řádně neskončí, je označené jako přerušené.

    dpi_aware: jestli program na Windows vypnul roztažení obrazu podle měřítka (mimo Windows None).
    """
    return {
        "participant": participant,
        "machine": machine,
        "machine_id": machine_id,
        **environment,
        "started_at": started_at.isoformat(timespec="seconds"),
        "ended_at": None,
        "aborted": True,
        "simulated": simulated,
        "block_order": block_order,
        "language": language,
        # Hodnocení námahy doplní krok 9.
        "seed": seed,
        "short": short,
        "effort_ratings": [],
        "planned_starts": planned_starts,
        "frame_rate_hz": round(frame_rate, 3),
        "window_mode": window_mode,
        "window_size_px": list(window_size),
        "px_per_cm": calibration.px_per_cm,
        "calibrated_at": calibration.calibrated_at,
        "dpi_aware": dpi_aware,
        "keyboard_backend": keyboard_backend,
        "timing_s": {
            "LIGHT_INTERVAL": LIGHT_INTERVAL,
            "FOREPERIODS": list(FOREPERIODS),
            "RESPONSE_WINDOW": RESPONSE_WINDOW,
            "REST_INTERVAL": REST_INTERVAL,
            "ANTICIPATION_THRESHOLD": ANTICIPATION_THRESHOLD,
            "DIGITS_DURATION": DIGITS_DURATION,
            "DIGITS_BLANK": DIGITS_BLANK,
            "RECALL_FEEDBACK_DURATION": RECALL_FEEDBACK_DURATION,
        },
        "practice_rounds": None,
        "dropped_frames_total": None,
    }


def finish_meta(
    meta: dict[str, object],
    ended_at: datetime,
    dropped_frames_total: int,
    practice_rounds: int,
) -> dict[str, object]:
    """Vrátí kopii metadat označenou jako řádně dokončené sezení."""
    return {
        **meta,
        "ended_at": ended_at.isoformat(timespec="seconds"),
        "aborted": False,
        "dropped_frames_total": dropped_frames_total,
        "practice_rounds": practice_rounds,
    }


def write_json(path: Path, data: dict[str, object]) -> None:
    """Uloží JSON (meta, počítač) přes dočasný soubor, aby pád nenechal půlku souboru."""
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    temporary.replace(path)


def px_per_cm_from_card(width_px: int) -> float:
    """Pixely na centimetr z šířky obdélníku srovnaného s kartou."""
    return round(width_px / CARD_WIDTH_CM, PX_PER_CM_DECIMALS)


def card_width_px(px_per_cm: float) -> int:
    """Šířka obdélníku karty v pixelech (výchozí bod kalibrace)."""
    return round(px_per_cm * CARD_WIDTH_CM)


def card_height_px(width_px: int) -> float:
    """Výška obdélníku karty v pixelech, v poměru stran karty."""
    return width_px * CARD_HEIGHT_CM / CARD_WIDTH_CM


def adjust_card_width(width_px: int, name: str) -> int:
    """Šipka změní šířku obdélníku (CALIBRATION_KEYS), jiná klávesa nic; nejméně 1 px."""
    return max(1, width_px + CALIBRATION_KEYS.get(name, 0))


def is_plausible_px_per_cm(px_per_cm: object) -> bool:
    """Je hodnota kalibrace věrohodná (číslo v rozsahu PX_PER_CM_MIN až PX_PER_CM_MAX)?"""
    is_number = isinstance(px_per_cm, int | float) and not isinstance(px_per_cm, bool)
    return is_number and PX_PER_CM_MIN <= px_per_cm <= PX_PER_CM_MAX


def provisional_px_per_cm(window_height: int) -> float:
    """Odhad pixelů na centimetr před první kalibrací (z obvyklé výšky displeje notebooku)."""
    return window_height / ASSUMED_SCREEN_HEIGHT_CM


def decimal_text(value: float) -> str:
    """Číslo na jedno desetinné místo s desetinnou čárkou (texty pro experimentátora)."""
    return f"{value:.1f}".replace(".", ",")


def calibration_screen_text() -> str:
    """Návod na kalibrační obrazovce s rozměry karty v mm."""
    return CALIBRATION_SCREEN.format(
        card_width=decimal_text(CARD_WIDTH_CM * MM_PER_CM),
        card_height=decimal_text(CARD_HEIGHT_CM * MM_PER_CM),
    )


def calibration_accepts_enter(width_px: int, adjusted: bool) -> bool:
    """Enter uloží kalibraci jen po úpravě šipkami a s věrohodnou hodnotou.

    Bez úpravy by šlo omylem potvrdit neměřený odhad (např. Enterem po psaní nicku).
    """
    return adjusted and is_plausible_px_per_cm(px_per_cm_from_card(width_px))


def calibration_value_text(width_px: int, adjusted: bool) -> str:
    """Řádek pod obdélníkem: šířka a pixely na centimetr, případně proč Enter nejde."""
    px_per_cm = px_per_cm_from_card(width_px)
    lines = [
        CALIBRATION_VALUE.format(width=width_px, px_per_cm=decimal_text(px_per_cm))
    ]
    if not is_plausible_px_per_cm(px_per_cm):
        lines.append(
            CALIBRATION_INVALID.format(
                minimum=round(PX_PER_CM_MIN), maximum=round(PX_PER_CM_MAX)
            )
        )
    if not adjusted:
        lines.append(CALIBRATION_ADJUST_FIRST)
    return "\n".join(lines)


def recalibrated(
    previous: Calibration | None,
    px_per_cm: float,
    window_size: tuple[int, int],
    calibrated_at: str,
) -> Calibration:
    """Výsledek kalibrace; beze změny hodnoty zůstane dosavadní kalibrace i s datem.

    Datum tak říká, kdy byla hodnota naměřena (simulace po K a Enteru zůstane bez data).
    """
    unchanged = (
        previous is not None
        and previous.px_per_cm == px_per_cm
        and previous.window_size == window_size
    )
    if unchanged:
        return previous
    return Calibration(px_per_cm, window_size, calibrated_at)


def calibration_note(calibration: Calibration) -> str:
    """Popis kalibrace na obrazovce nastavení (hodnota a datum, u simulace bez data)."""
    px_per_cm = decimal_text(calibration.px_per_cm)
    if calibration.calibrated_at is None:
        return CALIBRATION_NOTE_SIM.format(px_per_cm=px_per_cm)
    calibrated = datetime.fromisoformat(calibration.calibrated_at)
    date = f"{calibrated.day}. {calibrated.month}. {calibrated.year}"
    return CALIBRATION_NOTE.format(px_per_cm=px_per_cm, date=date)


def size_check_text() -> str:
    """Text obrazovky ověření velikosti: rozměry vlajky a lamp v cm."""
    return SIZE_CHECK_SCREEN.format(
        flag_width=decimal_text(FLAG_WIDTH),
        flag_height=decimal_text(FLAG_HEIGHT),
        lamp_diameter=decimal_text(2 * LAMP_RADIUS),
        lamp_spacing=decimal_text(LAMP_SPACING),
    )


def new_machine_id() -> str:
    """Nový anonymní identifikátor počítače (náhodný, nic o počítači neprozrazuje)."""
    return secrets.token_hex(MACHINE_ID_BYTES)


def is_valid_machine_id(machine_id: object) -> bool:
    """Má identifikátor počítače správný tvar (2 × MACHINE_ID_BYTES šestnáctkových znaků)?"""
    return (
        isinstance(machine_id, str)
        and len(machine_id) == 2 * MACHINE_ID_BYTES
        and all(char in MACHINE_ID_CHARS for char in machine_id)
    )


def is_valid_timestamp(text: object) -> bool:
    """Je to čas ve formátu ISO 8601 (jak ho zapisuje program)?"""
    if not isinstance(text, str):
        return False
    try:
        datetime.fromisoformat(text)
    except ValueError:
        return False
    return True


def parse_calibration(data: object) -> Calibration | None:
    """Kalibrace ze souboru počítače; neúplná nebo nevěrohodná = žádná."""
    if not isinstance(data, dict):
        return None
    size = data.get("window_size_px")
    calibrated_at = data.get("calibrated_at")
    if (
        not is_plausible_px_per_cm(data.get("px_per_cm"))
        or not isinstance(size, list)
        or len(size) != 2
        or not all(isinstance(side, int) for side in size)
        or not is_valid_timestamp(calibrated_at)
    ):
        return None
    return Calibration(float(data["px_per_cm"]), (size[0], size[1]), calibrated_at)


def load_machine_info(path: Path) -> MachineInfo:
    """Načte údaje o počítači; když soubor chybí nebo je poškozený, vytvoří nový identifikátor.

    Nový identifikátor se uloží až se sezením (save_machine_info po obrazovce nastavení).
    """
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return MachineInfo(new_machine_id())
    if not isinstance(data, dict) or not is_valid_machine_id(data.get("machine_id")):
        return MachineInfo(new_machine_id())
    return MachineInfo(data["machine_id"], parse_calibration(data.get("calibration")))


def save_machine_info(path: Path, info: MachineInfo) -> None:
    """Uloží identifikátor počítače a kalibraci do data/machine.json."""
    calibration = info.calibration
    write_json(
        path,
        {
            "machine_id": info.machine_id,
            "calibration": None
            if calibration is None
            else {
                "px_per_cm": calibration.px_per_cm,
                "window_size_px": list(calibration.window_size),
                "calibrated_at": calibration.calibrated_at,
            },
        },
    )


def calibration_for_window(
    info: MachineInfo, window_size: tuple[int, int]
) -> Calibration | None:
    """Uložená kalibrace, jen když platí pro tuto velikost okna (jinak je potřeba nová)."""
    calibration = info.calibration
    if calibration is None or calibration.window_size != window_size:
        return None
    return calibration


@dataclass(frozen=True)
class RunOptions:
    """Volby z příkazové řádky: simulace, start s Escapem (simulace), zkrácený plán."""

    simulated: bool = False
    escape_at: int | None = None
    short: bool = False
    seed: int | None = None


def parse_args(args: list[str]) -> RunOptions:
    """Přečte argumenty příkazové řádky (--sim, --sim-escape, --short, --seed=N).

    Neznámý argument (např. překlep --simm) je chyba, aby se omylem nespustil ostrý běh.
    Pevný seed jen se simulací: ostré sezení má seed vždy náhodný.
    """
    allowed = (SIM_FLAG, SIM_ESCAPE_FLAG, SHORT_FLAG)
    seed_prefix = SEED_FLAG + "="
    seeds = [
        arg.removeprefix(seed_prefix) for arg in args if arg.startswith(seed_prefix)
    ]
    unknown = [
        arg for arg in args if arg not in allowed and not arg.startswith(seed_prefix)
    ]
    if unknown:
        raise ValueError(
            f"Neznámý argument {unknown[0]!r}. Povolené: {', '.join(allowed)}, {seed_prefix}N."
        )
    simulated = SIM_FLAG in args or SIM_ESCAPE_FLAG in args
    valid_seed = len(seeds) == 1 and seeds[0].isdecimal() and int(seeds[0]) < SEED_MAX
    if seeds and not (valid_seed and simulated):
        raise ValueError(
            f"{seed_prefix}N jde jen jednou, s celým číslem 0 … {SEED_MAX - 1} a se simulací."
        )
    return RunOptions(
        simulated=simulated,
        escape_at=SIM_ESCAPE_AT if SIM_ESCAPE_FLAG in args else None,
        short=SHORT_FLAG in args,
        seed=int(seeds[0]) if seeds else None,
    )


def session_data_dir(data_root: Path, simulated: bool, nick: str) -> Path:
    """Složka pro data sezení: simulace, pilot a testy do podsložek, mimo ostrá data."""
    if simulated:
        return data_root / SIM_DIR_NAME
    for prefix in (PILOT_PREFIX, TEST_PREFIX):
        if nick.startswith(prefix):
            return data_root / prefix
    return data_root


def short_plan_allowed(simulated: bool, nick: str) -> bool:
    """Zkrácený plán (--short) jen pro simulaci a testovací nick test…, nikdy pro účastníka."""
    return session_data_dir(Path(), simulated, nick).name in (SIM_DIR_NAME, TEST_PREFIX)


def edit_text(text: str, name: str, char: str, allowed: str, max_length: int) -> str:
    """Upraví psaný text jedním stiskem: Backspace maže, povolený znak se připíše."""
    if name == BACKSPACE_KEY:
        return text[:-1]
    if len(char) == 1 and char in allowed and len(text) < max_length:
        return text + char
    return text


def is_valid_nick(nick: str) -> bool:
    """Nick: 2–16 znaků, malá písmena a–z, číslice, - a _ (docs/experiment.md)."""
    length_ok = NICK_MIN_LENGTH <= len(nick) <= NICK_MAX_LENGTH
    return length_ok and all(char in NICK_CHARS for char in nick)


def genuine_presses(keys: list, still_down: object | None) -> list:
    """Vynechá „fantomové“ stisky, které PsychoPy vyrobí z puštění klávesy po Shiftu.

    Puštění se páruje se stiskem podle napsaného znaku. Když Shift pustíte dřív než
    klávesu (Shift+minus = „_“, puštění = „-“), pár se nenajde a vznikne nový stisk.
    Skutečný stisk je mezi drženými klávesami (still_down) nebo už má délku stisku.
    still_down=None (simulace) = všechny stisky jsou skutečné.
    """
    if still_down is None:
        return keys
    return [
        key
        for key in keys
        if getattr(key, "duration", None) is not None
        or any(down is key for down in still_down)
    ]


@dataclass(frozen=True)
class NickInput:
    """Stav obrazovky s nickem: napsaný text, hláška a jestli se čeká na potvrzení."""

    text: str = ""
    message: str = ""
    awaiting_confirmation: bool = False
    done: bool = False


def nick_input_key(
    state: NickInput, name: str, char: str, exists: Callable[[str], bool]
) -> NickInput:
    """Zpracuje jednu klávesu na obrazovce s nickem a vrátí nový stav.

    Enter ověří nick; existující nick chce druhý Enter. Jakákoli úprava textu
    (i Backspace = „opravit“) hlášku i čekání na potvrzení zruší.
    """
    if name in ENTER_KEYS:
        if not is_valid_nick(state.text):
            return replace(state, message=NICK_INVALID, awaiting_confirmation=False)
        if state.awaiting_confirmation or not exists(state.text):
            return replace(state, done=True)
        return replace(
            state,
            message=NICK_EXISTS.format(nick=state.text),
            awaiting_confirmation=True,
        )
    text = edit_text(state.text, name, char, NICK_CHARS, NICK_MAX_LENGTH)
    if text == state.text:
        return state  # Shift, Caps Lock apod. hlášku ani potvrzení nezruší
    return NickInput(text=text)


def nick_from_filename(name: str) -> str | None:
    """Vytáhne nick z názvu souboru {nick}_{stroj}_{YYYY-MM-DD}_{HHMM}…; nick smí mít „_“."""
    parts = Path(name).stem.split("_")
    if len(parts) < 4 or parts[-3] not in MACHINE_CODES.values():
        return None
    return "_".join(parts[:-3])


def nick_exists(data_dir: Path, nick: str) -> bool:
    """Zjistí, jestli ve složce dat už je sezení se stejným nickem."""
    return any(nick_from_filename(path.name) == nick for path in data_dir.glob("*.csv"))


def count_completed_sessions(data_dir: Path, machine: str) -> int:
    """Spočítá dokončená ostrá sezení tohoto počítače (meta s aborted = false) v data/.

    Nepočítá pilot, testy ani simulace (ani kdyby omylem ležely přímo v data/) a data
    zkopírovaná z jiného počítače.
    """
    count = 0
    for meta_path in data_dir.glob("*" + META_SUFFIX):
        try:
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        simulated = bool(meta.get("simulated"))
        nick = str(meta.get("participant", ""))
        is_main = session_data_dir(data_dir, simulated, nick) == data_dir
        full = not meta.get("short")
        if (
            meta.get("aborted") is False
            and is_main
            and full
            and meta.get("machine") == machine
        ):
            count += 1
    return count


def assign_block_order(completed_sessions: int) -> str:
    """Střídání pořadí bloků na tomto počítači: sudý počet → ABBA, lichý → BAAB."""
    return BLOCK_ORDERS[completed_sessions % len(BLOCK_ORDERS)]


@dataclass(frozen=True)
class SettingsInfo:
    """Co obrazovka nastavení jen ukazuje: účastník, počítač, cílová složka, kalibrace.

    folder je klíč FOLDER_NOTE ("" = ostrá data), completed počet dokončených sezení.
    """

    nick: str
    machine: str
    machine_id: str
    folder: str
    completed: int
    calibration: Calibration


def settings_text(info: SettingsInfo, block_order: str, language: str) -> str:
    """Text obrazovky nastavení pro zvolené pořadí bloků a jazyk."""
    auto_order = assign_block_order(info.completed)
    return SETTINGS_SCREEN.format(
        nick=info.nick,
        machine=info.machine,
        machine_id=info.machine_id,
        folder=FOLDER_NOTE[info.folder],
        block_order=block_order,
        order_note=settings_order_note(block_order, auto_order, info.completed),
        language_name=LANGUAGE_NAMES[language],
        calibration=calibration_note(info.calibration),
    )


def settings_action(name: str) -> str | None:
    """Klávesa, která obrazovku nastavení opustí: Enter = začít, K = kalibrace, V = ověření."""
    if name in ENTER_KEYS:
        return SETTINGS_START
    return SETTINGS_ACTIONS.get(name)


def settings_order_note(block_order: str, auto_order: str, completed: int) -> str:
    """Poznámka k pořadí bloků: automatické, nebo ručně přepsané."""
    if block_order == auto_order:
        return ORDER_AUTO.format(completed=completed)
    return ORDER_MANUAL.format(auto_order=auto_order)


def apply_settings_key(name: str, block_order: str, language: str) -> tuple[str, str]:
    """Klávesa na obrazovce nastavení: A/B mění pořadí bloků, C/E jazyk účastníka."""
    return (
        BLOCK_ORDER_KEYS.get(name, block_order),
        LANGUAGE_KEYS.get(name, language),
    )


def digits_in_order(plan: list[Start], digits: dict[tuple[int, int], str]) -> list[str]:
    """Číslice sad plánu v pořadí, v jakém sady proběhnou (i prázdné u sad bez číslic)."""
    return [digits[key] for key in dict.fromkeys(set_keys(plan))]
