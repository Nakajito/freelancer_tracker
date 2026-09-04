"""Guard that every application module parses and imports cleanly.

``config/urls.py`` imports every views module, so a single unimportable file
takes down the entire URLconf and every request 500s. Lint does not cover this:
a ``SyntaxError`` aborts ruff's parse of the file, and an import-time error
(bad name, circular import) is not a syntax problem at all.

Note these tests are only meaningful under the project's own interpreter
(``requires-python = ">=3.14"``). Running them on an older Python reports false
failures for 3.14-only syntax such as PEP 758 unparenthesized ``except`` tuples.
"""

import ast
import importlib
from pathlib import Path

import pytest

APPS_DIR = Path(__file__).resolve().parent.parent / "apps"

PY_FILES = sorted(
    p for p in APPS_DIR.rglob("*.py") if "/migrations/" not in p.as_posix()
)

VIEW_MODULES = sorted(
    f"apps.{p.relative_to(APPS_DIR).with_suffix('').as_posix().replace('/', '.')}"
    for p in APPS_DIR.glob("*/views*.py")
)


@pytest.mark.parametrize("path", PY_FILES, ids=lambda p: p.name)
def test_source_file_parses(path: Path) -> None:
    """Every application source file is valid Python."""
    source = path.read_text(encoding="utf-8")
    try:
        ast.parse(source, filename=str(path))
    except SyntaxError as exc:  # pragma: no cover - failure path
        pytest.fail(f"{path} line {exc.lineno}: {exc.msg}")


@pytest.mark.parametrize("module", VIEW_MODULES)
def test_views_module_imports(module: str) -> None:
    """Every views module imports cleanly."""
    importlib.import_module(module)


def test_urlconf_loads() -> None:
    """The root URLconf resolves — proves no views module is broken."""
    from django.urls import get_resolver

    resolver = get_resolver()
    assert resolver.url_patterns
