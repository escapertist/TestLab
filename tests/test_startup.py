"""Сборка приложения и жизненный цикл."""

import tomllib
from pathlib import Path

from fastapi.testclient import TestClient

import testlab.__main__ as entrypoint
from testlab.__main__ import create_app
from testlab.errors import InvalidTokenError, NotFoundError, PermissionDeniedError
from tests.helpers import iter_routes


def collect_routes(app) -> list[tuple[str, str]]:
    return [
        (method, route.path)
        for route in iter_routes(app)
        for method in getattr(route, "methods", set())
    ]


def test_routes_are_unique():
    pairs = collect_routes(create_app())

    assert len(pairs) == len(set(pairs))


def test_auth_me_registered_once():
    paths = [path for _, path in collect_routes(create_app()) if path == "/auth/me"]

    assert paths == ["/auth/me"]


def test_domain_exception_handlers_registered():
    app = create_app()

    assert NotFoundError in app.exception_handlers
    assert PermissionDeniedError in app.exception_handlers
    assert InvalidTokenError in app.exception_handlers


def test_materials_routes_registered():
    paths = {path for _, path in collect_routes(create_app())}

    assert {
        "/materials",
        "/materials/{material_id}",
        "/materials/{material_id}/file",
        "/materials/{material_id}/tests",
        "/auth/register",
        "/auth/login",
        "/auth/me",
    } <= paths


def test_lifespan_disposes_engine_on_shutdown(monkeypatch):
    class FakeEngine:
        def __init__(self) -> None:
            self.disposed = 0

        async def dispose(self) -> None:
            self.disposed += 1

    engine = FakeEngine()
    initialized: list[object] = []

    async def fake_init_db(async_engine, drop: bool = False) -> None:
        initialized.append(async_engine)

    monkeypatch.setattr("testlab.__main__.init_db", fake_init_db)
    monkeypatch.setattr("testlab.__main__.async_engine", engine)

    with TestClient(create_app()) as client:
        assert client.get("/docs").status_code == 200
        assert initialized == [engine]
        assert engine.disposed == 0

    assert engine.disposed == 1


def test_main_starts_uvicorn(monkeypatch):
    calls: dict = {}

    def fake_run(target, host=None, port=None, reload=False):
        calls.update(target=target, host=host, port=port, reload=reload)

    monkeypatch.setattr(entrypoint.uvicorn, "run", fake_run)
    entrypoint.main()

    assert calls == {
        "target": "testlab.__main__:app",
        "host": "127.0.0.1",
        "port": 8000,
        "reload": True,
    }


def test_console_script_points_to_callable():
    project_file = Path(__file__).resolve().parents[1] / "pyproject.toml"
    data = tomllib.loads(project_file.read_text(encoding="utf-8"))

    assert data["project"]["scripts"]["testlab"] == "testlab.__main__:main"


def test_api_docs_cover_implemented_routes():
    docs = (Path(__file__).resolve().parents[1] / "docs" / "API.md").read_text(encoding="utf-8")

    for path in (
        "/auth/register",
        "/auth/login",
        "/auth/me",
        "/materials",
        "/materials/{material_id}",
        "/materials/{material_id}/file",
        "/materials/{material_id}/tests",
    ):
        assert path in docs
    assert "## 3. Материалы (teacher) — реализовано" in docs
    assert "### `POST /materials/{material_id}/tests` — реализовано" in docs
