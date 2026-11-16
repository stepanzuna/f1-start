"""Režim simulace: falešná klávesnice a scénář odpovědí (bez PsychoPy).

Přesunuto z logic.py beze změny kódu (refaktorizace 14. 11. 2026).
"""

import itertools
from collections import deque
from dataclasses import dataclass
from types import SimpleNamespace

from config import (
    BACKSPACE_KEY,
    DIGITS,
    EFFORT_DIGITS,
    END_KEY,
    FLAG_HEIGHT,
    FLAG_POS,
    FLAG_WIDTH,
    INSTRUCTION_SCREENS,
    LAMP_RADIUS,
    LAMP_SPACING,
    LAMP_Y,
    N_LAMPS,
    PRACTICE_CONTINUE_KEY,
    PRACTICE_REPEAT_KEY,
    SIM_EARLY_PRESS,
    SIM_EFFORT_RATINGS,
    SIM_GO_CYCLE,
    SIM_INTRO_KEYS,
    SIM_KEYBOARD_BACKEND,
    SIM_MACHINE_ID,
    SIM_NOGO_CYCLE,
    SIM_PRACTICE_ROUNDS,
    SIM_PRESS_RT,
    SIM_PX_PER_CM,
    SIM_RECALL_CYCLE,
    SIM_WINDOW_MARGIN,
    SIM_WINDOW_SCALE,
    START_KEY,
)
from logic import (
    Calibration,
    MachineInfo,
    Start,
    build_practice,
    build_session,
    classify_press,
    digits_in_order,
    group_sets,
    outcome_without_press,
    split_blocks,
)


def make_sim_scenario(plan: list[Start], escape_at: int | None = None) -> list[str]:
    """Přiřadí každému startu typ odpovědi; go a no-go starty se střídají dokola zvlášť.

    S escape_at (pořadí startu od 1) se v tom startu stiskne Escape a sezení se přeruší.
    """
    go_responses = itertools.cycle(SIM_GO_CYCLE)
    nogo_responses = itertools.cycle(SIM_NOGO_CYCLE)
    scenario = [
        next(nogo_responses if start.is_nogo else go_responses) for start in plan
    ]
    if escape_at is not None:
        scenario[escape_at - 1] = "escape"
    return scenario


def sim_window_size(screen: tuple[int, int], pixel_ratio: float) -> tuple[int, int]:
    """Velikost okna simulace: podíl displeje, ale aspoň tolik, aby se vešly všechny podněty.

    Okno se zadává v bodech displeje, podněty jsou v cm a simulace je kreslí podle
    SIM_PX_PER_CM; pixel_ratio je počet pixelů na bod (Retina 2, jinak 1).
    """
    half_width_cm = max(FLAG_WIDTH / 2, (N_LAMPS - 1) / 2 * LAMP_SPACING + LAMP_RADIUS)
    half_height_cm = max(FLAG_POS[1] + FLAG_HEIGHT / 2, abs(LAMP_Y) + LAMP_RADIUS)
    half_width = half_width_cm * SIM_PX_PER_CM
    half_height = half_height_cm * SIM_PX_PER_CM
    needed = (
        round(2 * (half_width + SIM_WINDOW_MARGIN) / pixel_ratio),
        round(2 * (half_height + SIM_WINDOW_MARGIN) / pixel_ratio),
    )
    return tuple(
        min(side, max(round(side * SIM_WINDOW_SCALE), minimum))
        for side, minimum in zip(screen, needed, strict=True)
    )


def sim_machine_info(window_size: tuple[int, int]) -> MachineInfo:
    """Simulace nekalibruje: pevný identifikátor počítače a SIM_PX_PER_CM pro okno simulace."""
    return MachineInfo(SIM_MACHINE_ID, Calibration(SIM_PX_PER_CM, window_size, None))


def expected_outcome(response: str, is_nogo: bool) -> str:
    """Výsledek, který má program vyhodnotit pro danou simulovanou odpověď."""
    if response == "early":
        return "jump_start"
    if response == "none":
        return outcome_without_press(is_nogo)
    return classify_press(SIM_PRESS_RT[response], is_nogo)


def sim_recall_answer(digits: str, set_number: int) -> str:
    """Odpověď, kterou simulace napíše při vybavení sady číslo set_number (od 1)."""
    pattern = SIM_RECALL_CYCLE[(set_number - 1) % len(SIM_RECALL_CYCLE)]
    if pattern == "wrong":
        return digits[:-1] + next(d for d in DIGITS if d != digits[-1])
    if pattern == "short":
        return digits[:1]
    return digits  # "correct" i "corrected"


def sim_recall_keys(digits: str, set_number: int) -> list[str]:
    """Klávesy, kterými simulace vybavení napíše (u "corrected" překlep a Backspace)."""
    pattern = SIM_RECALL_CYCLE[(set_number - 1) % len(SIM_RECALL_CYCLE)]
    typo = [next(d for d in DIGITS if d != digits[0]), BACKSPACE_KEY]
    prefix = typo if pattern == "corrected" else []
    return [*prefix, *sim_recall_answer(digits, set_number), "return"]


def sim_sequence(
    block_order: str, seed: int, short: bool
) -> tuple[list[Start], list[list[str]], list[list[str]]]:
    """Co simulace projde: SIM_PRACTICE_ROUNDS testovacích kol, pak ostrou část.

    Vrací (všechny starty v pořadí, číslice sad po testovacích kolech, číslice ostrých sad
    po blocích).
    """
    rounds = build_practice(seed, SIM_PRACTICE_ROUNDS)
    plan, digits = build_session(block_order, seed, short)
    starts = [start for round_starts, _ in rounds for start in round_starts] + plan
    practice_digits = [[d for d in digits_in_order(s, ds) if d] for s, ds in rounds]
    main_digits = [
        [d for d in digits_in_order(block, digits) if d] for block in split_blocks(plan)
    ]
    return starts, practice_digits, main_digits


def sim_effort(block: int) -> str:
    """Hodnocení bloku (od 1) na Paasově škále, které simulace napíše."""
    return SIM_EFFORT_RATINGS[(block - 1) % len(SIM_EFFORT_RATINGS)]


def make_sim_typed_keys(
    practice_digits: list[list[str]], main_digits: list[list[str]]
) -> list[str]:
    """Všechny klávesy simulace v pořadí obrazovek celého sezení.

    Úvodní obrazovky, instrukce (mezerník), testovací kola (úvod, předěl před sadou,
    vybavení, R / mezerník), začátek měření, po každém bloku vybavení jeho sad, hodnocení
    a pauza (po posledním bloku ne) a závěrečná obrazovka.
    """
    keys = list(SIM_INTRO_KEYS)
    keys += [START_KEY] * len(INSTRUCTION_SCREENS)
    set_number = 0
    for round_number, round_digits in enumerate(practice_digits, start=1):
        keys += [START_KEY, START_KEY]  # úvod testovacího kola, předěl před sadou
        for digits in round_digits:
            set_number += 1
            keys += sim_recall_keys(digits, set_number)
        last = round_number == len(practice_digits)
        keys.append(PRACTICE_CONTINUE_KEY if last else PRACTICE_REPEAT_KEY)
    keys.append(START_KEY)  # začátek měření
    for block, block_digits in enumerate(main_digits, start=1):
        for digits in block_digits:
            set_number += 1
            keys += sim_recall_keys(digits, set_number)
        # Nejdřív jiné číslo, pak změna na hodnocení bloku a Enter (ověří změnu výběru).
        other = next(d for d in EFFORT_DIGITS if d != sim_effort(block))
        keys += [other, sim_effort(block), "return"]
        if block < len(main_digits):
            keys.append(START_KEY)  # pauza mezi bloky
    keys.append(END_KEY)
    return keys


def starts_written_before(sequence: list[Start], escape_at: int) -> int:
    """Kolik startů je zapsaných, když Escape přijde ve startu escape_at (od 1).

    Zapisuje se po celých skupinách (sada, v části 1 testovacího kola po startu).
    """
    written = 0
    for group in group_sets(sequence):
        if written + len(group) >= escape_at:
            break
        written += len(group)
    return written


@dataclass
class SimulatedKeyPress:
    """Simulovaný stisk se stejnými atributy, jaké program čte z KeyPress v PsychoPy.

    name je název klávesy (např. "return"), code napsaný znak (jako char z iohub).
    """

    name: str
    rt: float | None
    code: str = ""


def sim_key(name: str) -> SimulatedKeyPress:
    """Simulovaný stisk klávesy na obrazovce s textem (písmeno, Enter, Backspace)."""
    code = name if len(name) == 1 else {"return": "\n"}.get(name, "")
    return SimulatedKeyPress(name, None, code)


class SimulatedKeyboard:
    """Falešná klávesnice pro simulaci: stiskne podle scénáře, čas počítá ve snímcích.

    Napodobuje tu část keyboard.Keyboard, kterou program používá: první getKeys() s mezerníkem
    po clearEvents() (začátek startu) vezme další odpověď ze scénáře, clock.reset() (volané
    při zhasnutí) spustí měření reakce, getKeys() bez keyList vrací klávesy napsané
    na obrazovkách s textem. getKeys() se volá jednou za snímek.
    """

    def __init__(
        self, scenario: list[str], rate: float, typed_keys: list[str] | None = None
    ) -> None:
        self._responses = iter(scenario)
        self._typed = deque(typed_keys or [])
        self._rate = rate
        self._response: str | None = None
        self._started = False
        self._polls_since_clear = 0
        self._polls_since_reset: int | None = None
        self.clock = SimpleNamespace(reset=self._reset)

    def getBackend(self) -> str:
        """Název backendu do metadat."""
        return SIM_KEYBOARD_BACKEND

    def clearEvents(self) -> None:
        """Smaže čekající stisky; další start si vezme novou odpověď ze scénáře."""
        self._response = None
        self._started = False
        self._polls_since_clear = 0
        self._polls_since_reset = None

    def _reset(self) -> None:
        """Zhasnutí lamp: od teď se měří reakční čas."""
        self._polls_since_reset = 0

    def _due_press(self) -> SimulatedKeyPress | None:
        """Vrátí stisk, pokud podle scénáře v tomto snímku nastal, jinak None."""
        if self._response in (None, "none"):
            return None
        if self._response == "escape":
            return SimulatedKeyPress("escape", None)
        if self._response == "early":
            before_reset = self._polls_since_reset is None
            if before_reset and self._polls_since_clear / self._rate >= SIM_EARLY_PRESS:
                return SimulatedKeyPress("space", None)
            return None
        rt = SIM_PRESS_RT[self._response]
        if (
            self._polls_since_reset is not None
            and self._polls_since_reset / self._rate >= rt
        ):
            return SimulatedKeyPress("space", rt)
        return None

    def getKeys(
        self, keyList: list[str] | None = None, waitRelease: bool = False
    ) -> list[SimulatedKeyPress]:
        """Jedno čtení klávesnice za snímek, stejné volání jako u keyboard.Keyboard.

        Bez keyList (obrazovky s textem) vrátí další napsanou klávesu. S mezerníkem
        v keyList jde o start: první čtení po clearEvents vezme odpověď ze scénáře.
        Proto obrazovky mimo start čtou klávesy vždy bez keyList (viz CLAUDE.md).
        """
        if keyList is None:
            return [sim_key(self._typed.popleft())] if self._typed else []
        if "space" in keyList and not self._started:
            self._response = next(self._responses, None)
            self._started = True
        press = self._due_press()
        self._polls_since_clear += 1
        if self._polls_since_reset is not None:
            self._polls_since_reset += 1
        if press is None or press.name not in keyList:
            return []
        self._response = None
        return [press]
