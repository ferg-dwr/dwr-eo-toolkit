"""Packaging regression tests.

Two failures these guard against, both found in v0.4.0:

1. `[tool.setuptools] packages = ["dwr_eo_toolkit"]` declared only the
   top-level package. The built wheel contained exactly one .py file and every
   documented import raised ModuleNotFoundError on a clean install. It went
   unnoticed because `pip install -e .` and the docker-compose bind mount both
   read the working tree instead of the installed package.

2. `__init__.py` imported DownloadManager eagerly, so `from
   dwr_eo_toolkit.filters import Query` -- which needs nothing third-party --
   required apscheduler.

Both are invisible to ordinary unit tests, which run against the source tree.
These build a real wheel and inspect it.
"""

from __future__ import annotations

import ast
import subprocess
import sys
import tomllib
import zipfile
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC = REPO_ROOT / "src"
PACKAGE = "dwr_eo_toolkit"

# Every subpackage that must ship. Add to this list when adding a subpackage.
EXPECTED_SUBPACKAGES = [
    "api",
    "cli",
    "core",
    "database",
    "download_manager",
    "filters",
    "monitoring",
    "providers",
    "providers/adapters",
]

# Third-party top-level modules each subpackage is permitted to import.
# Enforces the extras boundary: if `filters` starts importing sqlalchemy,
# the base install silently stops working and this test says so.
ALLOWED_IMPORTS: dict[str, set[str]] = {
    "core": {"requests"},
    "providers": {"earthaccess"},
    "filters": set(),
    "monitoring": set(),
    "cli": {"click"},
    "download_manager": {"requests", "apscheduler"},
    "database": {"sqlalchemy", "dotenv"},
    "api": {"fastapi", "uvicorn", "pydantic", "sqlalchemy", "starlette"},
}

# Subpackages installable with only the base dependencies.
BASE_ONLY_SUBPACKAGES = ["core", "providers", "filters", "monitoring"]

THIRD_PARTY = {
    "fastapi",
    "uvicorn",
    "sqlalchemy",
    "psycopg2",
    "alembic",
    "pydantic",
    "earthaccess",
    "requests",
    "numpy",
    "pandas",
    "apscheduler",
    "click",
    "dotenv",
    "starlette",
    "httpx",
}


# --------------------------------------------------------------------------
# Wheel contents
# --------------------------------------------------------------------------


@pytest.fixture(scope="module")
def wheel(tmp_path_factory) -> Path:
    """Build a wheel once and hand its path to the tests that need it."""
    out = tmp_path_factory.mktemp("wheel")
    proc = subprocess.run(
        [sys.executable, "-m", "build", "--wheel", "--outdir", str(out), str(REPO_ROOT)],
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        pytest.fail(
            "wheel build failed -- is `build` installed? "
            "(pip install 'dwr-eo-toolkit[dev]')\n"
            f"{proc.stdout[-2000:]}\n{proc.stderr[-2000:]}"
        )
    wheels = list(out.glob("*.whl"))
    assert len(wheels) == 1, f"expected one wheel, got {wheels}"
    return wheels[0]


@pytest.fixture(scope="module")
def wheel_names(wheel: Path) -> list[str]:
    with zipfile.ZipFile(wheel) as zf:
        return zf.namelist()


@pytest.mark.packaging
@pytest.mark.slow
@pytest.mark.parametrize("subpackage", EXPECTED_SUBPACKAGES)
def test_wheel_contains_all_subpackages(wheel_names: list[str], subpackage: str) -> None:
    """Every subpackage ships in the wheel.

    Regression: setuptools `packages = ["dwr_eo_toolkit"]` dropped all of them.
    """
    prefix = f"{PACKAGE}/{subpackage}/"
    matching = [n for n in wheel_names if n.startswith(prefix) and n.endswith(".py")]
    assert matching, (
        f"No modules from {prefix} in the wheel. Check that pyproject.toml uses\n"
        f'    [tool.setuptools.packages.find]\n    where = ["src"]\n'
        f"rather than an explicit `packages = [...]` list."
    )


@pytest.mark.packaging
@pytest.mark.slow
def test_wheel_module_count_matches_source(wheel_names: list[str]) -> None:
    """The wheel ships as many modules as the source tree holds."""
    on_disk = {
        p.relative_to(SRC).as_posix() for p in SRC.rglob("*.py") if "__pycache__" not in p.parts
    }
    in_wheel = {n for n in wheel_names if n.endswith(".py")}
    missing = sorted(on_disk - in_wheel)
    assert not missing, f"{len(missing)} module(s) missing from wheel: {missing[:10]}"


@pytest.mark.packaging
@pytest.mark.slow
def test_wheel_top_level_is_single_package(wheel: Path) -> None:
    """src-layout resolved correctly: `src` must not become the package name."""
    with zipfile.ZipFile(wheel) as zf:
        entry = next(n for n in zf.namelist() if n.endswith("top_level.txt"))
        top = zf.read(entry).decode().split()
    assert top == [PACKAGE], f"unexpected top-level packages: {top}"


# --------------------------------------------------------------------------
# Dependency boundaries  (fast -- static analysis, no build)
# --------------------------------------------------------------------------


def _third_party_imports(subpackage: str) -> set[str]:
    found: set[str] = set()
    for path in (SRC / PACKAGE / subpackage).rglob("*.py"):
        if "__pycache__" in path.parts:
            continue
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8", errors="replace"))):
            names: list[str] = []
            if isinstance(node, ast.Import):
                names = [a.name for a in node.names]
            elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
                names = [node.module]
            found |= {n.split(".")[0].lower() for n in names} & THIRD_PARTY
    return found


@pytest.mark.parametrize("subpackage", sorted(ALLOWED_IMPORTS))
def test_subpackage_stays_within_its_extra(subpackage: str) -> None:
    """A subpackage may only import what its declared extra installs.

    If this fails, either the import is wrong or pyproject's extras need
    updating -- but decide deliberately, because widening a base-install
    subpackage's imports makes `pip install dwr-eo-toolkit` heavier for
    everyone.
    """
    directory = SRC / PACKAGE / subpackage
    if not directory.exists():
        pytest.skip(f"{subpackage} not present")
    unexpected = _third_party_imports(subpackage) - ALLOWED_IMPORTS[subpackage]
    assert not unexpected, (
        f"{subpackage} imports {sorted(unexpected)}, which is outside its extra. "
        f"Allowed: {sorted(ALLOWED_IMPORTS[subpackage]) or 'nothing third-party'}"
    )


def test_declared_dependencies_are_actually_imported() -> None:
    """Base dependencies should be used. Catches leftovers after a refactor.

    numpy and pandas were declared in v0.4.0 and imported nowhere in src/.
    Runtime-only drivers (psycopg2, alembic) legitimately never appear in an
    import statement, so only base dependencies are checked.
    """
    pyproject = tomllib.loads((REPO_ROOT / "pyproject.toml").read_text())
    declared = {
        d.split(">=")[0].split("[")[0].split("==")[0].strip().lower()
        for d in pyproject["project"]["dependencies"]
    }
    imported: set[str] = set()
    for sub in [p.name for p in (SRC / PACKAGE).iterdir() if p.is_dir()]:
        imported |= _third_party_imports(sub)
    # normalise distribution names to import names
    aliases = {"python-dotenv": "dotenv", "psycopg2-binary": "psycopg2"}
    declared = {aliases.get(d, d) for d in declared}
    unused = declared - imported
    assert not unused, f"declared as base dependencies but never imported: {sorted(unused)}"


# --------------------------------------------------------------------------
# Lazy top-level imports
# --------------------------------------------------------------------------


def test_init_has_no_eager_subpackage_imports() -> None:
    """__init__.py must not import subpackages at module scope.

    Regression: eager `from dwr_eo_toolkit.download_manager import
    DownloadManager` meant every import path required apscheduler.
    TYPE_CHECKING-guarded imports are fine -- they never run.
    """
    tree = ast.parse((SRC / PACKAGE / "__init__.py").read_text())
    offenders = [
        ast.unparse(node)
        for node in tree.body  # module scope only
        if isinstance(node, (ast.Import, ast.ImportFrom)) and PACKAGE in ast.unparse(node)
    ]
    assert not offenders, (
        "eager subpackage import(s) at module scope in __init__.py: "
        f"{offenders}. Move them under `if TYPE_CHECKING:` and resolve at "
        "runtime via module-level __getattr__."
    )


@pytest.mark.parametrize("subpackage", BASE_ONLY_SUBPACKAGES)
def test_base_subpackage_imports_in_subprocess(subpackage: str) -> None:
    """Base-install subpackages import without optional dependencies present.

    Run in a subprocess so a sibling test that already imported the heavy
    modules cannot mask the failure via sys.modules.
    """
    blocked = ["apscheduler", "fastapi", "uvicorn", "sqlalchemy", "psycopg2", "alembic"]
    code = (
        "import sys\n"
        f"for m in {blocked!r}:\n"
        "    sys.modules[m] = None\n"
        f"import {PACKAGE}.{subpackage}\n"
        "print('ok')\n"
    )
    proc = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True)
    assert proc.returncode == 0, (
        f"{PACKAGE}.{subpackage} could not be imported without optional "
        f"dependencies:\n{proc.stderr[-1500:]}"
    )


def test_lazy_attribute_error_is_normal() -> None:
    """An unknown attribute raises AttributeError, not KeyError."""
    import dwr_eo_toolkit

    with pytest.raises(AttributeError):
        dwr_eo_toolkit.NoSuchThing


def test_dir_lists_public_names() -> None:
    import dwr_eo_toolkit

    assert set(dwr_eo_toolkit.__all__) <= set(dir(dwr_eo_toolkit))
