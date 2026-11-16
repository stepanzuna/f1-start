"""Testy kalibrace velikosti, údajů o počítači a obrazovky nastavení (bez okna PsychoPy)."""

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from config import (
    ASSUMED_SCREEN_HEIGHT_CM,
    CALIBRATION_ADJUST_FIRST,
    CALIBRATION_INVALID,
    CARD_HEIGHT_CM,
    CARD_WIDTH_CM,
    ENTER_KEYS,
    MACHINE_ID_BYTES,
    PX_PER_CM_MAX,
    PX_PER_CM_MIN,
    SETTINGS_CALIBRATE,
    SETTINGS_CHECK_SIZE,
    SETTINGS_START,
    SIM_MACHINE_ID,
    SIM_PX_PER_CM,
)
from logic import (
    Calibration,
    MachineInfo,
    SettingsInfo,
    adjust_card_width,
    calibration_accepts_enter,
    calibration_for_window,
    calibration_note,
    calibration_screen_text,
    calibration_value_text,
    card_height_px,
    card_width_px,
    decimal_text,
    is_plausible_px_per_cm,
    is_valid_machine_id,
    load_machine_info,
    make_meta,
    new_machine_id,
    parse_calibration,
    provisional_px_per_cm,
    px_per_cm_from_card,
    recalibrated,
    save_machine_info,
    settings_action,
    settings_text,
    size_check_text,
)
from simulation import sim_machine_info

SAMPLE_TIME = datetime(2026, 11, 16, 17, 20, tzinfo=timezone(timedelta(hours=1)))
WINDOW = (3024, 1964)
CALIBRATION = Calibration(50.35, WINDOW, SAMPLE_TIME.isoformat(timespec="seconds"))


def test_card_width_matches_macbook() -> None:
    """MacBook Pro 14" (50 px/cm, pixel PsychoPy = bod): karta 85,6 mm má 428 px a naopak."""
    assert card_width_px(50.0) == 428
    assert px_per_cm_from_card(428) == 50.0


def test_card_width_roundtrip() -> None:
    """Šířka → px/cm → šířka vrátí stejný počet pixelů (kalibrace se neposouvá)."""
    for width in range(1, 2000):
        assert card_width_px(px_per_cm_from_card(width)) == width


def test_card_keeps_aspect_ratio() -> None:
    """Obdélník má poměr stran karty ID-1."""
    assert card_height_px(856) == pytest.approx(856 * CARD_HEIGHT_CM / CARD_WIDTH_CM)


@pytest.mark.parametrize(
    ("name", "expected"),
    [("left", 855), ("right", 857), ("down", 846), ("up", 866), ("a", 856)],
)
def test_adjust_card_width(name: str, expected: int) -> None:
    """Šipky vlevo/vpravo mění šířku o 1 px, dolů/nahoru o 10 px, jiné klávesy nic."""
    assert adjust_card_width(856, name) == expected


def test_card_width_stays_positive() -> None:
    """Obdélník nezmizí: šířka je aspoň 1 px."""
    assert adjust_card_width(5, "down") == 1


@pytest.mark.parametrize(
    ("value", "plausible"),
    [
        (PX_PER_CM_MIN, True),
        (PX_PER_CM_MAX, True),
        (55.6, True),
        (PX_PER_CM_MIN - 0.1, False),
        (PX_PER_CM_MAX + 0.1, False),
        ("100", False),
        (True, False),
        (None, False),
    ],
)
def test_plausible_px_per_cm(value: object, plausible: bool) -> None:
    """Věrohodná kalibrace je číslo v rozsahu PX_PER_CM_MIN až PX_PER_CM_MAX."""
    assert is_plausible_px_per_cm(value) is plausible


def test_provisional_estimate_is_close_on_macbook() -> None:
    """Odhad před první kalibrací vyjde na MacBooku skoro přesně (982 pix, výška 19,6 cm)."""
    assert provisional_px_per_cm(982) == pytest.approx(982 / ASSUMED_SCREEN_HEIGHT_CM)
    assert abs(card_width_px(provisional_px_per_cm(982)) - 428) <= 2


def test_calibration_value_text_warns_outside_range() -> None:
    """Pod obdélníkem je hodnota; mimo věrohodný rozsah i upozornění."""
    assert calibration_value_text(428, True) == "Šířka obdélníku 428 px = 50,0 px/cm"
    warning = CALIBRATION_INVALID.format(
        minimum=round(PX_PER_CM_MIN), maximum=round(PX_PER_CM_MAX)
    )
    assert calibration_value_text(100, True).endswith(warning)


def test_calibration_value_text_before_adjusting() -> None:
    """Dokud se šířka neupraví šipkami, řádek řekne, proč Enter nejde."""
    assert calibration_value_text(428, False).endswith(CALIBRATION_ADJUST_FIRST)


@pytest.mark.parametrize(
    ("width", "adjusted", "accepted"),
    [(428, True, True), (428, False, False), (100, True, False), (2000, True, False)],
)
def test_calibration_accepts_enter(width: int, adjusted: bool, accepted: bool) -> None:
    """Enter uloží jen po úpravě šipkami (neměřený odhad nejde odklepnout) a v rozsahu."""
    assert calibration_accepts_enter(width, adjusted) is accepted


def test_calibration_screen_text_has_card_size() -> None:
    """Návod uvádí rozměry karty z konstant v mm."""
    assert "(85,6 × 54,0 mm)" in calibration_screen_text()


def test_unchanged_recalibration_keeps_date() -> None:
    """K a Enter beze změny nechá dosavadní kalibraci i s datem (simulace zůstane bez data)."""
    later = "2026-11-20T09:00:00+01:00"
    assert recalibrated(CALIBRATION, 50.35, WINDOW, later) == CALIBRATION
    simulated = Calibration(SIM_PX_PER_CM, (605, 393), None)
    assert recalibrated(simulated, SIM_PX_PER_CM, (605, 393), later) == simulated


@pytest.mark.parametrize(
    ("previous", "px_per_cm"), [(None, 50.35), (CALIBRATION, 50.0)]
)
def test_new_calibration_gets_date(
    previous: Calibration | None, px_per_cm: float
) -> None:
    """První kalibrace nebo změněná hodnota dostane nové datum."""
    later = "2026-11-20T09:00:00+01:00"
    assert recalibrated(previous, px_per_cm, WINDOW, later) == Calibration(
        px_per_cm, WINDOW, later
    )


def test_calibration_note() -> None:
    """Obrazovka nastavení ukáže hodnotu s desetinnou čárkou a datum kalibrace."""
    assert calibration_note(CALIBRATION) == "50,4 px/cm, kalibrace 16. 11. 2026"
    assert "simulace" in calibration_note(Calibration(50.0, WINDOW, None))


def test_cm_text() -> None:
    """Desetinná čárka, jedno desetinné místo."""
    assert decimal_text(5.0) == "5,0"
    assert decimal_text(0.8) == "0,8"


def test_size_check_text_has_stimulus_sizes() -> None:
    """Text ověření pravítkem uvádí rozměry vlajky a lamp v cm."""
    text = size_check_text()
    assert "10,0 × 6,0 cm" in text
    assert "průměr světla 1,6 cm" in text
    assert "po 2,4 cm" in text


def test_new_machine_id() -> None:
    """Identifikátor počítače je náhodný a má správný tvar."""
    first, second = new_machine_id(), new_machine_id()
    assert is_valid_machine_id(first)
    assert len(first) == 2 * MACHINE_ID_BYTES
    assert first != second


@pytest.mark.parametrize(
    "machine_id", ["A1B2C3D4", "a1b2c3", "a1b2c3d4e", "a1b2c3dz", 7]
)
def test_invalid_machine_id(machine_id: object) -> None:
    """Neplatný identifikátor: jiná délka, velká písmena, jiné znaky, ne text."""
    assert not is_valid_machine_id(machine_id)


def test_missing_machine_file_gives_new_id(tmp_path: Path) -> None:
    """Bez souboru počítače: nový identifikátor, žádná kalibrace, nic se nezapíše."""
    path = tmp_path / "machine.json"
    info = load_machine_info(path)
    assert is_valid_machine_id(info.machine_id)
    assert info.calibration is None
    assert not path.exists()


def test_machine_file_roundtrip(tmp_path: Path) -> None:
    """Uložený identifikátor a kalibrace se načtou beze změny."""
    path = tmp_path / "machine.json"
    info = MachineInfo("a1b2c3d4", CALIBRATION)
    save_machine_info(path, info)
    assert load_machine_info(path) == info
    assert not path.with_name(path.name + ".tmp").exists()


def test_corrupted_machine_file_gives_new_id(tmp_path: Path) -> None:
    """Poškozený soubor (napůl zapsaný, jiný obsah) program neshodí."""
    path = tmp_path / "machine.json"
    path.write_text('{"machine_id": "a1b2', encoding="utf-8")
    assert is_valid_machine_id(load_machine_info(path).machine_id)
    path.write_text("[1, 2]", encoding="utf-8")
    assert is_valid_machine_id(load_machine_info(path).machine_id)


@pytest.mark.parametrize(
    "calibration",
    [
        None,
        "100",
        {"px_per_cm": 5.0, "window_size_px": [1920, 1080], "calibrated_at": "x"},
        {"px_per_cm": 55.6, "window_size_px": [1920], "calibrated_at": "x"},
        {"px_per_cm": 55.6, "window_size_px": [1920, 1080.5], "calibrated_at": "x"},
        {"px_per_cm": 55.6, "window_size_px": [1920, 1080]},
        {"px_per_cm": 55.6, "window_size_px": [1920, 1080], "calibrated_at": "včera"},
    ],
)
def test_invalid_calibration_is_ignored(calibration: object) -> None:
    """Neúplná nebo nevěrohodná kalibrace v souboru = žádná (vyžádá se nová)."""
    assert parse_calibration(calibration) is None


def test_invalid_calibration_keeps_machine_id(tmp_path: Path) -> None:
    """Špatná kalibrace v souboru nezmění identifikátor počítače."""
    path = tmp_path / "machine.json"
    data = {"machine_id": "a1b2c3d4", "calibration": {"px_per_cm": 1000.0}}
    path.write_text(json.dumps(data), encoding="utf-8")
    assert load_machine_info(path) == MachineInfo("a1b2c3d4", None)


def test_calibration_only_for_same_window() -> None:
    """Kalibrace platí jen pro stejnou velikost okna (jiné rozlišení = nová kalibrace)."""
    info = MachineInfo("a1b2c3d4", CALIBRATION)
    assert calibration_for_window(info, WINDOW) == CALIBRATION
    assert calibration_for_window(info, (1920, 1080)) is None
    assert calibration_for_window(MachineInfo("a1b2c3d4"), WINDOW) is None


def test_sim_machine_info_is_fixed() -> None:
    """Simulace má pevnou kalibraci pro své okno a pevný identifikátor."""
    info = sim_machine_info((605, 393))
    assert info.machine_id == SIM_MACHINE_ID
    assert is_valid_machine_id(SIM_MACHINE_ID)
    assert calibration_for_window(info, (605, 393)) == Calibration(
        SIM_PX_PER_CM, (605, 393), None
    )


def test_settings_text_shows_machine_and_calibration() -> None:
    """Nastavení ukáže identifikátor počítače, kalibraci a klávesy K a V."""
    info = SettingsInfo("anna", "mac", "a1b2c3d4", "", 2, CALIBRATION)
    text = settings_text(info, "ABBA", "en")
    assert "Počítač: mac (a1b2c3d4)" in text
    assert "50,4 px/cm, kalibrace 16. 11. 2026" in text
    assert "K = kalibrovat znovu, V = ověřit pravítkem" in text
    assert "automaticky podle 2 dokončených sezení" in text
    assert "English" in text


@pytest.mark.parametrize(
    ("name", "action"),
    [
        *((key, SETTINGS_START) for key in ENTER_KEYS),
        ("k", SETTINGS_CALIBRATE),
        ("v", SETTINGS_CHECK_SIZE),
        ("a", None),
        ("e", None),
    ],
)
def test_settings_action(name: str, action: str | None) -> None:
    """Enter začne sezení, K a V otevřou kalibraci a ověření, ostatní klávesy zůstanou."""
    assert settings_action(name) == action


def test_meta_has_calibration() -> None:
    """Meta obsahuje identifikátor počítače, kalibraci a DPI awareness."""
    meta = make_meta(
        participant="test",
        machine="win",
        started_at=SAMPLE_TIME,
        environment={},
        frame_rate=60.0,
        window_mode="fullscr",
        window_size=(1920, 1080),
        keyboard_backend="iohub",
        planned_starts=16,
        block_order="ABBA",
        language="cs",
        seed=1,
        short=False,
        simulated=False,
        machine_id="a1b2c3d4",
        calibration=Calibration(55.607, (1920, 1080), "2026-11-16T17:20:00+01:00"),
        dpi_aware=True,
    )
    assert meta["machine_id"] == "a1b2c3d4"
    assert meta["px_per_cm"] == 55.607
    assert meta["calibrated_at"] == "2026-11-16T17:20:00+01:00"
    assert meta["dpi_aware"] is True
