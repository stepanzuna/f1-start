"""Testy pravidel projektu: zakázaná volání, importy a schválené parametry.

Když test parametrů selže, parametr se změnil bez dohody. Test neupravuj, zeptej se.
"""

import ast
from pathlib import Path

import pytest

import config

ROOT = Path(__file__).parent.parent
SOURCE_FILES = sorted(ROOT.glob("*.py"))
PSYCHOPY_FREE = ("config.py", "logic.py", "simulation.py", "check_data.py")
# Kdo smí importovat koho: nižší vrstva nesmí záviset na vyšší (main → screens → simulation
# → logic → config), aby čistá logika šla testovat bez okna.
FORBIDDEN_IMPORTS = {
    "config.py": {"logic", "simulation", "screens", "main"},
    "logic.py": {"simulation", "screens", "main"},
    "simulation.py": {"screens", "main"},
    "screens.py": {"main"},
    "check_data.py": {"screens", "main"},
}
FORBIDDEN_CALLS = {("time", "sleep"), ("core", "wait"), ("random", "choice")}
SINGLE_PLATFORM_MODULES = {"AppKit", "Foundation", "objc", "win32api", "ctypes.windll"}

# Schválené parametry z docs/experiment.md (Parametry, rozhodnuto 12. 11. 2026).
# Velikosti podnětů v cm od 16. 11. 2026 (krok 2k, schváleno autorem): dřívější pixely
# na MacBooku Pro 14" děleno 50 px/cm (pixel PsychoPy na Retině = bod displeje).
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
    "LAMP_RADIUS": 0.8,
    "LAMP_SPACING": 2.4,
    "LAMP_Y": -1.8,
    "FLAG_WIDTH": 10.0,
    "FLAG_HEIGHT": 6.0,
    "FLAG_POS": (0, 3.6),
    "CARD_WIDTH_CM": 8.56,  # karta ID-1 (ISO/IEC 7810), 85,60 × 53,98 mm
    "CARD_HEIGHT_CM": 5.398,
    "PX_PER_CM_MIN": 20.0,
    "PX_PER_CM_MAX": 200.0,
    # Texty v cm (krok 2k): výška písma a pozice řádků
    "TEXT_HEIGHT": 0.8,
    "FEEDBACK_HEIGHT": 1.2,
    "DIGITS_HEIGHT": 1.6,
    "FEEDBACK_Y": 1.2,
    "PROMPT_Y": 2.4,
    "INPUT_Y": 0.0,
    "MESSAGE_Y": -2.4,
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


@pytest.mark.parametrize("name", FORBIDDEN_IMPORTS)
def test_module_layers(name: str) -> None:
    """Modul neimportuje vyšší vrstvu (čistá logika zůstane bez PsychoPy a bez okna)."""
    modules = {
        m.split(".")[0] for m in imported_modules(list(ast.walk(parse(ROOT / name))))
    }
    assert not modules & FORBIDDEN_IMPORTS[name]


def test_psychopy_imported_after_quieting_log() -> None:
    """main.py načte PsychoPy (visual, keyboard, screens) až po ztišení logování konzole."""
    body = parse(ROOT / "main.py").body
    quiet = next(
        i
        for i, node in enumerate(body)
        if isinstance(node, ast.Expr) and "setLevel" in ast.unparse(node)
    )
    loud = {"screens", "pyglet", "psychopy.visual", "psychopy.hardware"}
    for i, node in enumerate(body):
        names = imported_modules([node])
        if isinstance(node, ast.ImportFrom) and node.module == "psychopy":
            names |= {f"psychopy.{alias.name}" for alias in node.names}
        if names & loud:
            assert i > quiet, (
                f"main.py:{node.lineno} importuje {names & loud} před setLevel"
            )


def test_dpi_awareness_before_window_imports() -> None:
    """main.py zapne DPI awareness (Windows) dřív, než načte visual, screens a pyglet.

    PsychoPy při importu visual vytvoří skryté okno; DPI awareness musí být nastavená před ním.
    """
    body = parse(ROOT / "main.py").body
    dpi = next(
        i
        for i, node in enumerate(body)
        if isinstance(node, ast.Assign) and "enable_dpi_awareness" in ast.unparse(node)
    )
    window = {"screens", "pyglet", "psychopy.visual", "psychopy.hardware"}
    for i, node in enumerate(body):
        names = imported_modules([node])
        if isinstance(node, ast.ImportFrom) and node.module == "psychopy":
            names |= {f"psychopy.{alias.name}" for alias in node.names}
        if names & window:
            assert i > dpi, f"main.py:{node.lineno} importuje {names & window} před DPI"
