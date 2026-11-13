"""Testy pravidel projektu: zakázaná volání, importy a schválené parametry.

Když test parametrů selže, parametr se změnil bez dohody. Test neupravuj, zeptej se.
"""

import ast
from pathlib import Path

import pytest

import config

ROOT = Path(__file__).parent.parent
SOURCE_FILES = sorted(ROOT.glob("*.py"))
PSYCHOPY_FREE = ("config.py", "logic.py", "check_data.py")
FORBIDDEN_CALLS = {("time", "sleep"), ("core", "wait"), ("random", "choice")}
SINGLE_PLATFORM_MODULES = {"AppKit", "Foundation", "objc", "win32api", "ctypes.windll"}

# Schválené parametry z docs/experiment.md (Parametry, rozhodnuto 12. 11. 2026).
APPROVED_PARAMETERS = {
    "LIGHT_INTERVAL": 1.0,
    "FOREPERIODS": [0.5, 1.25, 2.0, 2.75],
    "RESPONSE_WINDOW": 1.5,
    "REST_INTERVAL": 1.0,
    "ANTICIPATION_THRESHOLD": 0.1,
    "DIGITS_DURATION": 4.0,
    "DIGITS_BLANK": 0.5,
    "STARTS_PER_SET": 3,
    "DIGITS_PER_LOAD": {"none": 0, "low": 2, "high": 6},
    "N_LAMPS": 5,
    "LAMP_RADIUS": 40,
    "LAMP_SPACING": 120,
    "LAMP_Y": -90,
    "FLAG_WIDTH": 500,
    "FLAG_HEIGHT": 300,
    "FLAG_POS": (0, 180),
    "EXPECTED_FRAME_RATE": 60,
    "FRAME_RATE_TOLERANCE": 1.0,
    "GO_PER_FOREPERIOD": 9,
    "NOGO_PER_FOREPERIOD": 3,
    "MAX_NOGO_RUN": 2,
    "BLOCK_LOADS": {"A": "low", "B": "high"},
    # Testovací kolo: 4 starty bez číslic (1 no-go) + 1 sada s nízkou zátěží.
    "PRACTICE_SINGLE_NOGO": 1,
    "PRACTICE_LOAD": "low",
}


def parse(path: Path) -> ast.Module:
    """Načte zdrojový soubor jako strom syntaxe (AST)."""
    return ast.parse(path.read_text(encoding="utf-8"), filename=str(path))


def imported_modules(nodes: list[ast.stmt]) -> set[str]:
    """Vrátí jména modulů importovaných v daných příkazech."""
    names = set()
    for node in nodes:
        if isinstance(node, ast.Import):
            names.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.add(node.module)
    return names


@pytest.mark.parametrize("name", PSYCHOPY_FREE)
def test_no_psychopy_import(name: str) -> None:
    """config.py, logic.py a check_data.py neimportují PsychoPy (testují se bez okna)."""
    path = ROOT / name
    if not path.exists():
        pytest.skip(f"{name} zatím neexistuje")
    modules = imported_modules(list(ast.walk(parse(path))))
    assert not any(module.split(".")[0] == "psychopy" for module in modules)


@pytest.mark.parametrize("path", SOURCE_FILES, ids=lambda path: path.name)
def test_no_forbidden_calls(path: Path) -> None:
    """Žádné time.sleep, core.wait ani random.choice: časuje se ve snímcích, náhoda v plánu."""
    for node in ast.walk(parse(path)):
        if isinstance(node, ast.ImportFrom) and node.module:
            module = node.module.split(".")[-1]
            for alias in node.names:
                if (module, alias.name) in FORBIDDEN_CALLS:
                    pytest.fail(
                        f"{path.name}:{node.lineno} importuje {module}.{alias.name}"
                    )
        if (
            isinstance(node, ast.Attribute)
            and isinstance(node.value, ast.Name)
            and (node.value.id, node.attr) in FORBIDDEN_CALLS
        ):
            pytest.fail(f"{path.name}:{node.lineno} volá {node.value.id}.{node.attr}")


@pytest.mark.parametrize("path", SOURCE_FILES, ids=lambda path: path.name)
def test_no_single_platform_import_at_module_level(path: Path) -> None:
    """Knihovny jen pro jeden systém se importují uvnitř větve sys.platform, ne nahoře."""
    modules = imported_modules(parse(path).body)
    assert not modules & SINGLE_PLATFORM_MODULES


@pytest.mark.parametrize("name", APPROVED_PARAMETERS)
def test_approved_parameters(name: str) -> None:
    """Parametry experimentu odpovídají schváleným hodnotám v docs/experiment.md."""
    assert getattr(config, name) == APPROVED_PARAMETERS[name]


def test_real_window_mode_is_full_screen() -> None:
    """Ostrý běh má režim celé obrazovky; menší okno simulace mezi povolenými není."""
    assert config.WINDOW_MODE in config.WINDOW_MODES
    assert config.SIM_WINDOW_MODE not in config.WINDOW_MODES
