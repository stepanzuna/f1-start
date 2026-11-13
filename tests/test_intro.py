"""Testy úvodních obrazovek: psaní textu, nick, pořadí bloků, jazyk (bez okna PsychoPy)."""

import json
from pathlib import Path

import pytest

from config import (
    ENTER_KEYS,
    LANGUAGE_NAMES,
    LANGUAGES,
    NICK_CHARS,
    NICK_MAX_LENGTH,
    SIM_INTRO_KEYS,
    SIM_LANGUAGE,
    SIM_NICK,
    TEXTS,
)
from logic import (
    NickInput,
    SimulatedKeyboard,
    apply_settings_key,
    assign_block_order,
    count_completed_sessions,
    edit_text,
    genuine_presses,
    is_valid_nick,
    nick_exists,
    nick_from_filename,
    nick_input_key,
    settings_order_note,
)


def never_exists(_nick: str) -> bool:
    """Žádný nick ještě neexistuje."""
    return False


def type_keys(state: NickInput, keys: list[tuple[str, str]]) -> NickInput:
    """Napíše posloupnost kláves (název, znak) na obrazovce s nickem."""
    for name, char in keys:
        state = nick_input_key(state, name, char, never_exists)
    return state


@pytest.mark.parametrize(
    ("text", "name", "char", "expected"),
    [
        ("an", "n", "n", "ann"),
        ("ann", "backspace", "", "an"),
        ("", "backspace", "", ""),
        ("an", "a", "A", "an"),  # velké písmeno (Shift) se nepíše
        ("an", "2", "ě", "an"),  # česká horní řada bez Shiftu
        ("an", "2", "2", "an2"),  # česká horní řada se Shiftem = číslice
        ("an", "minus", "_", "an_"),  # Shift + minus
        ("an", "lshift", "", "an"),  # samotný modifikátor nic nepíše
        ("a" * NICK_MAX_LENGTH, "b", "b", "a" * NICK_MAX_LENGTH),
    ],
)
def test_edit_text(text: str, name: str, char: str, expected: str) -> None:
    """Backspace maže, povolený znak (z char, ne z názvu klávesy) se připíše."""
    assert edit_text(text, name, char, NICK_CHARS, NICK_MAX_LENGTH) == expected


@pytest.mark.parametrize(
    ("nick", "valid"),
    [
        ("an", True),
        ("anna_k-2", True),
        ("a" * 16, True),
        ("a", False),
        ("a" * 17, False),
        ("Anna", False),
        ("anna k", False),
        ("anička", False),
        ("", False),
    ],
)
def test_is_valid_nick(nick: str, valid: bool) -> None:
    """Nick: 2–16 znaků, malá písmena a–z, číslice, - a _."""
    assert is_valid_nick(nick) is valid


def test_nick_input_invalid_then_fixed() -> None:
    """Příliš krátký nick ukáže chybu, po opravě Enter nick přijme."""
    state = type_keys(NickInput(), [("x", "x"), ("return", "\n")])
    assert state.message
    assert not state.done
    state = type_keys(state, [("backspace", ""), ("s", "s"), ("i", "i")])
    assert state.message == ""
    state = type_keys(state, [("return", "\n")])
    assert state.done
    assert state.text == "si"


def test_nick_input_existing_needs_confirmation() -> None:
    """Existující nick: první Enter varuje, druhý potvrdí; úprava varování zruší."""

    def exists(nick: str) -> bool:
        return nick == "anna"

    state = NickInput(text="anna")
    state = nick_input_key(state, "return", "\n", exists)
    assert state.awaiting_confirmation
    assert "anna" in state.message
    assert not state.done
    edited = nick_input_key(state, "backspace", "", exists)
    assert edited == NickInput(text="ann")
    confirmed = nick_input_key(state, "num_enter", "\n", exists)
    assert confirmed.done


@pytest.mark.parametrize(
    ("name", "nick"),
    [
        ("anna_k_mac_2026-11-13_0905.csv", "anna_k"),
        ("an_win_2026-12-01_1400.csv", "an"),
        ("x_meta.json", None),
        ("anna_linux_2026-11-13_0905.csv", None),
    ],
)
def test_nick_from_filename(name: str, nick: str | None) -> None:
    """Nick se čte z názvu zprava, takže smí obsahovat podtržítko."""
    assert nick_from_filename(name) == nick


def test_nick_exists(tmp_path: Path) -> None:
    """Existence nicku podle CSV; „anna“ není totéž co „anna_k“."""
    (tmp_path / "anna_k_mac_2026-11-13_0905.csv").write_text("", encoding="utf-8")
    assert nick_exists(tmp_path, "anna_k")
    assert not nick_exists(tmp_path, "anna")
    assert not nick_exists(tmp_path, "k")


def write_meta_file(path: Path, **meta: object) -> None:
    """Zapíše zkušební metadata."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(meta), encoding="utf-8")


def test_count_completed_sessions(tmp_path: Path) -> None:
    """Počítají se jen dokončená ostrá sezení tohoto počítače, ne testy, pilot ani podsložky."""
    meta = {"aborted": False, "machine": "mac", "participant": "anna"}
    write_meta_file(tmp_path / "a_mac_2026-11-13_0900_meta.json", **meta)
    write_meta_file(tmp_path / "b_mac_2026-11-13_0901_meta.json", **meta)
    write_meta_file(
        tmp_path / "c_mac_2026-11-13_0902_meta.json", **meta | {"aborted": True}
    )
    write_meta_file(
        tmp_path / "w_win_2026-11-13_0902_meta.json", **meta | {"machine": "win"}
    )
    write_meta_file(
        tmp_path / "t_mac_2026-11-13_0903_meta.json", **meta | {"participant": "test"}
    )
    write_meta_file(
        tmp_path / "s_mac_2026-11-13_0903_meta.json", **meta | {"simulated": True}
    )
    write_meta_file(
        tmp_path / "z_mac_2026-11-13_0903_meta.json", **meta | {"short": True}
    )
    write_meta_file(tmp_path / "pilot" / "pilot1_mac_2026-11-13_0903_meta.json", **meta)
    write_meta_file(tmp_path / "sim" / "sim_mac_2026-11-13_0904_meta.json", **meta)
    (tmp_path / "d_mac_2026-11-13_0905_meta.json").write_text(
        "{nedopsáno", encoding="utf-8"
    )
    assert count_completed_sessions(tmp_path, "mac") == 2
    assert count_completed_sessions(tmp_path, "win") == 1


def test_assign_block_order() -> None:
    """Sudý počet dokončených sezení → ABBA, lichý → BAAB."""
    assert [assign_block_order(n) for n in range(4)] == ["ABBA", "BAAB", "ABBA", "BAAB"]


def test_apply_settings_key() -> None:
    """A/B mění pořadí bloků, C/E jazyk, ostatní klávesy nic."""
    assert apply_settings_key("b", "ABBA", "cs") == ("BAAB", "cs")
    assert apply_settings_key("a", "BAAB", "cs") == ("ABBA", "cs")
    assert apply_settings_key("e", "ABBA", "cs") == ("ABBA", "en")
    assert apply_settings_key("c", "ABBA", "en") == ("ABBA", "cs")
    assert apply_settings_key("x", "ABBA", "en") == ("ABBA", "en")


def test_texts_have_same_keys_in_all_languages() -> None:
    """Každý text pro účastníka existuje ve všech jazycích se stejnými proměnnými."""
    assert set(TEXTS) == set(LANGUAGES) == set(LANGUAGE_NAMES)
    keys = set(TEXTS[LANGUAGES[0]])
    for language in LANGUAGES:
        assert set(TEXTS[language]) == keys
        for key in keys:
            placeholders = {
                part.split("}")[0] for part in TEXTS[language][key].split("{")[1:]
            }
            reference = TEXTS[LANGUAGES[0]][key]
            assert placeholders == {
                part.split("}")[0] for part in reference.split("{")[1:]
            }


def test_simulated_intro_typing() -> None:
    """Klávesy simulace projdou obrazovkou s nickem a nastavení: nick sim, jazyk EN."""
    kb = SimulatedKeyboard([], 60.0, list(SIM_INTRO_KEYS))
    state = NickInput()
    while not state.done:
        for key in kb.getKeys(waitRelease=False):
            state = nick_input_key(state, key.name, key.code, never_exists)
    block_order, language = "ABBA", "cs"
    while True:
        keys = kb.getKeys(waitRelease=False)
        if any(key.name in ENTER_KEYS for key in keys):
            break
        for key in keys:
            block_order, language = apply_settings_key(key.name, block_order, language)
    assert state.text == SIM_NICK
    assert language == SIM_LANGUAGE
    assert kb.getKeys(waitRelease=False) == []


def test_settings_order_note() -> None:
    """Poznámka ukáže automatické pořadí, nebo že bylo přepsáno ručně."""
    assert "3 dokončených" in settings_order_note("BAAB", "BAAB", 3)
    assert "automaticky by bylo BAAB" in settings_order_note("ABBA", "BAAB", 3)


def test_nick_input_modifier_keeps_warning() -> None:
    """Samotný Shift (nic se nenapíše) varování o existujícím nicku nezruší."""
    state = NickInput(text="anna", message="x", awaiting_confirmation=True)
    assert nick_input_key(state, "lshift", "", never_exists) == state


class FakeKey:
    """Stisk jako z PsychoPy: name, code a duration (None = ještě nepuštěno)."""

    def __init__(self, name: str, code: str, duration: float | None = None) -> None:
        self.name = name
        self.code = code
        self.duration = duration


def test_genuine_presses_drops_phantom() -> None:
    """Shift+minus = „_“ je držený (skutečný), puštění po Shiftu „-“ je fantom."""
    underscore = FakeKey("minus", "_")
    phantom = FakeKey("minus", "-")
    released = FakeKey("a", "a", duration=0.1)
    still_down = [underscore]
    keys = [underscore, phantom, released]
    assert genuine_presses(keys, still_down) == [underscore, released]
    assert genuine_presses(keys, None) == keys


def test_simulated_start_after_text_screens() -> None:
    """clearEvents na obrazovkách s textem nespotřebuje odpověď scénáře."""
    kb = SimulatedKeyboard(["fast", "normal"], 60.0, ["a"])
    kb.clearEvents()
    assert [key.name for key in kb.getKeys(waitRelease=False)] == ["a"]
    kb.clearEvents()
    kb.clearEvents()  # začátek startu
    kb.getKeys(keyList=["space", "escape"])
    kb.clock.reset()
    presses = [kb.getKeys(keyList=["space", "escape"]) for _ in range(10)]
    assert [keys[0].rt for keys in presses if keys] == [0.05]
