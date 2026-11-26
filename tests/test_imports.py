"""Правила зависимостей между слоями (AST-разбор импортов)."""

import ast
from collections.abc import Iterator
from pathlib import Path

import testlab
from testlab.models.enums import UserRole

PACKAGE_ROOT = Path(testlab.__file__).parent

FORBIDDEN: dict[str, set[str]] = {
    "routers": {
        "testlab.models",
        "testlab.repositories",
        "testlab.database",
        "testlab.infrastructure",
        "testlab.llm",
        "langchain_core",
        "langchain_gigachat",
    },
    "services": {
        "fastapi",
        "starlette",
        "sqlalchemy",
        "httpx",
        "langchain_core",
        "langchain_gigachat",
    },
    "repositories": {"testlab.services", "testlab.infrastructure", "testlab.llm"},
    "llm": {
        "testlab.services",
        "testlab.repositories",
        "testlab.routers",
        "testlab.database",
        "fastapi",
        "sqlalchemy",
    },
    "schemas": {
        "testlab.models",
        "testlab.services",
        "testlab.repositories",
        "testlab.infrastructure",
        "testlab.database",
        "testlab.llm",
    },
    "infrastructure": {"testlab.models", "testlab.services", "testlab.repositories"},
}

# Единственное разрешённое исключение: схемы берут перечисления из моделей.
ALLOWED: dict[str, set[str]] = {"schemas": {"testlab.models.enums"}}


def iter_imports(path: Path) -> Iterator[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                yield alias.name
        elif isinstance(node, ast.ImportFrom):
            if node.module is None:
                continue
            yield "." * node.level + node.module


def is_forbidden(module: str, forbidden: str, allowed: set[str] | None = None) -> bool:
    for item in allowed or ():
        if module == item or module.startswith(item + "."):
            return False
    return module == forbidden or module.startswith(forbidden + ".")


def layer_files(layer: str) -> list[Path]:
    return sorted((PACKAGE_ROOT / layer).rglob("*.py"))


def test_layer_imports():
    violations: list[str] = []
    for layer, forbidden in FORBIDDEN.items():
        allowed = ALLOWED.get(layer, set())
        for path in layer_files(layer):
            for module in iter_imports(path):
                for rule in forbidden:
                    if is_forbidden(module, rule, allowed):
                        violations.append(f"{path.relative_to(PACKAGE_ROOT)}: {module} (запрещено {rule})")

    assert violations == []


def test_schemas_may_import_only_models_enums():
    assert is_forbidden("testlab.models.enums", "testlab.models", ALLOWED["schemas"]) is False
    assert is_forbidden("testlab.models.test", "testlab.models", ALLOWED["schemas"]) is True


def test_legacy_modules_removed():
    assert not (PACKAGE_ROOT / "llm.py").exists()
    assert not (PACKAGE_ROOT / "exceptions.py").exists()
    assert not (PACKAGE_ROOT / "domain").exists()
    assert not (PACKAGE_ROOT / "infrastructure" / "llm.py").exists()


def test_enums_are_defined_in_models():
    assert UserRole.__module__ == "testlab.models.enums"


def test_services_do_not_commit():
    for path in layer_files("services"):
        assert "session.commit" not in path.read_text(encoding="utf-8")
