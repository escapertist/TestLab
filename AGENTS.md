# AGENTS.md

## Role
You are a Python backend developer for this project. Reply briefly, focus on technical substance.

## Communication
- **Always respond to the user in Russian.**
- Code, identifiers, and commit messages in English. User-facing HTTP messages, LLM prompts, and
  comments in Russian — the existing code does this, keep it.
- Be concise. No filler words. No greetings, no closing remarks.
- Code examples over long explanations.

## Project Overview
`testlab` is a FastAPI backend for teacher test generation. Uploading a PDF material
(`POST /materials`) validates it and persists the file plus the material row — no LLM call. A separate
action (`POST /materials/{material_id}/tests`) reads the stored file, asks the LLM (GigaChat) for a
test (5 closed + 2 open questions) and persists it; the test comes back with questions, options, and
rubrics. An existing test makes the action answer `409`, a model failure answers `502` and leaves no
test.

## Architecture
Layered, stateful, single service:

`routers` → `services` → `repositories` → `models` (`SQLAlchemy`), with `schemas` for I/O,
`infrastructure` for file and PDF adapters, `llm` for everything that talks to the model (the only
topic-named package), `dependencies` for DI wiring, and cross-cutting modules at the package root.

Allowed dependencies (checked by `tests/test_imports.py`):

| Module | May import | Forbidden |
|---|---|---|
| `routers/*` | `schemas`, `services`, `dependencies`, `errors` | `models`, `repositories`, `database`, `infrastructure`, `llm` |
| `services/*` | `models`, `repositories`, `errors`, `llm`, `infrastructure` (adapters) | `fastapi`, `sqlalchemy`, `httpx` |
| `repositories/*` | `models`, `errors`, `sqlalchemy` | `services`, `infrastructure`, `llm` |
| `llm/*` | `models`, `errors`, `config`, `httpx` | `services`, `routers`, `repositories`, `database`, `fastapi` |
| `schemas/*` | `models.enums` (only this module), `pydantic` | the rest of `models`, `services`, `repositories`, `infrastructure`, `database`, `llm` |
| `infrastructure/*` | `config`, `errors` | `models`, `services`, `repositories` |
| `dependencies/*` | everything (composition root) | business logic beyond wiring |

Rules:
- Routers parse input, call a service, return a schema. **No** `try/except` and no DB access.
- Domain errors are raised by services (or repositories when mapping persistence failures) and mapped
  to HTTP centrally in `errors.register_exception_handlers`.
- One transaction per use case: repositories only `flush`; `UnitOfWork.commit/rollback` is called by
  the service.
- Services never know `httpx`/`sqlalchemy`/`fastapi`; model calls live in `llm/`, files and PDFs in
  `infrastructure/`.
- A compensating action (deleting a just-saved file) belongs to the service that owns the use case.
- Enums are column types, so they are defined in `testlab.models.enums`; import them from there.
- Everything about the model lives in `llm/`. Do not add other topic-named packages — new code goes
  into the layer package that matches its job.

## Project Layout
`src`-layout package, distribution `testlab`.

- `src/testlab/__main__.py` — `create_app()`, lifespan (creates tables, disposes the pool on
  shutdown), `main()` runs uvicorn on `127.0.0.1:8000` with reload.
- `src/testlab/errors.py` — domain exceptions (`ConflictError` → `409` among them) +
  `register_exception_handlers(app)`.
- `src/testlab/database.py` — `Base`, `create_engine` (enables `PRAGMA foreign_keys` via the `begin`
  event), `get_db`, `init_db`.
- `src/testlab/security.py` — Argon2 password hashing.
- `src/testlab/llm/` — `client.py` (GigaChat OAuth + chat, retry on 401), `prompt.py` (`SYSTEM_PROMPT`,
  `JSON_EXAMPLE`, `build_user_prompt`), `generation.py` (DTO + `parse_generated_test`: JSON fence
  stripping, 5+2 composition, closed/open validation, `points`).
- `src/testlab/infrastructure/` — `pdf.py` (`extract_text`), `storage.py` (`FileStorage` protocol with
  `save`/`read`/`delete`, `LocalFileStorage`).
- `src/testlab/routers/` — `user.py` (`/auth`), `material.py` (`/materials`, five endpoints),
  `test.py` (`POST /materials/{material_id}/tests`, tag `tests`).
- `src/testlab/services/` — `user.py` (register/login/token), `auth.py` (token → user, role check),
  `material.py` (`upload_pdf`: validate → check text layer → save file and row; list/detail/file/delete),
  `test.py` (`generate_for_material`: ownership → `409` → `FileStorage.read` → text → LLM → one commit).
- `src/testlab/repositories/` — `uow.py` (`UnitOfWork`), `user.py`, `material.py`, `test.py`.
- `src/testlab/models/` — `user.py`, `material.py`, `test.py`, `enums.py` (column enums:
  `UserRole`, `TestStatus`, `QuestionType`, `QuestionSource`); `__init__.py` imports all models so
  `Base.metadata` is complete — keep it updated.
- `src/testlab/schemas/` — `common.py` (`UtcDatetime` serializer), `user.py`, `material.py`,
  `test.py` (`TestCreateRequest`); Pydantic v2, `from_attributes=True` for ORM.
- `src/testlab/dependencies/` — `uow.py` (`get_uow`), `user.py` (`get_user_service`), `auth.py`
  (`get_current_user`, `get_current_teacher`, `CurrentUser`, `CurrentTeacher`), `material.py`
  (`get_material_service`, `get_file_storage`, `get_llm_client`), `test.py` (`get_test_service`).
- `src/testlab/config/` — `base_config.py` (finds `.env` at the repo root), `db_config.py`,
  `llm_config.py`, `app_config.py` (`settings = AppConfig()`, imported everywhere).
- `src/testlab/init_db.py` — CLI `testlab-init-db [--reset]`.
- `tests/` — pytest (`asyncio_mode = "auto"`), `tests/helpers.py` holds the LLM double and fixtures
  helpers; `tests/llm/` covers the parser and the client; `tests/conftest.py` overrides
  `get_db`/`get_uow`/`get_file_storage`/`get_llm_client`.
- `docs/` — `API.md`, `er.md`, `sql_scripts.sql`; `openspec/` — OpenSpec change artifacts.

## Tech Stack
- Python `>=3.15`; `.python-version` pins `3.15`; package manager `uv`; `uv_build` backend.
- FastAPI + Uvicorn, SQLAlchemy 2 async + `aiosqlite` (default `sqlite+aiosqlite:///./testlab.db`,
  `asyncpg` available), Pydantic v2 + pydantic-settings, `pwdlib[argon2]`, `pypdf`, `httpx`.
- LLM: plain `httpx` calls to GigaChat OAuth and `/chat/completions` (model from config, default
  `GigaChat`). No LangChain.
- Tests: `pytest` + `pytest-asyncio` (dev group). `ruff` has a `[tool.ruff]` section:
  `select = ["E4", "E7", "E9", "F", "I", "UP", "B"]`, `ignore = ["B008"]`.

## Configuration
`settings` is instantiated at import from `AppConfig` with safe defaults — never require an env var
at import time. Every parameter has a default in `src/testlab/config/*_config.py`, so the service
starts without `.env`. `.env` in the repo root is local-only (gitignored) and overrides
`DB_URL`, `DB_ECHO`, `GIGACHAT_CREDENTIALS`, `GIGACHAT_SCOPE`, `GIGACHAT_MODEL`,
`GIGACHAT_VERIFY_SSL`, `GIGACHAT_TIMEOUT`, `GIGACHAT_MAX_INPUT_CHARS`, `UPLOADS_DIR`,
`UPLOADS_MAX_BYTES`. There is no tracked `.env` template: defaults live in the config classes, so
do not add a second copy of them as an example file.
`GIGACHAT_CREDENTIALS` is `client_id:secret` in base64; when empty, test creation
(`POST /materials/{material_id}/tests`) fails with `502`.

## Data Model
Implemented: `users`, `materials`, `tests`, `questions`, `closed_question_options`,
`open_question_rubrics`. `assignments`, `results`, `answers` exist only in `docs/er.md`.
IDs are `String(36)` UUIDs in the DB and `UUID` in schemas; timestamps are `DateTime(timezone=True)`
with `default=datetime.now(UTC)` and are serialized as `...Z` by `schemas.common.UtcDatetime`.
`tests` has a `generation_params` JSON column and `questions` a `source` enum (`llm` / `manual`).
SQLite enforces `ON DELETE CASCADE` only because the `begin` listener issues `PRAGMA foreign_keys=ON`.

## Auth
`POST /auth/register`, `POST /auth/login`, `GET /auth/me`. The token is the raw user id (a stand-in
for JWT) sent as `Bearer`; `AuthService.authenticate` resolves it, `require_teacher` enforces the
role. `/materials` and `POST /materials/{material_id}/tests` are role-guarded and material ownership
is enforced in SQL (`teacher_id`), so a foreign material looks like a missing one (`404`).

## Commands
Run from the repo root; `src` must be importable (editable/`uv sync` install).

| Canonical | In the agent environment (Windows) |
|---|---|
| `uv sync` | `uv sync` (global `uv`; the venv has no `uv.exe`) |
| `python -m testlab` | `.\.venv\Scripts\python.exe -m testlab` |
| `testlab-init-db [--reset]` | `.\.venv\Scripts\testlab-init-db.exe [--reset]` |
| `uv run ruff check .` | `.\.venv\Scripts\python.exe -m ruff check . --no-cache` |
| `uv run pytest -q` | `.\.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider` |
| `uv add <package>` | `uv add <package>` |

Notes:
- `python -m testlab` runs with `reload=True`; a reload supervisor needs named pipes, which a
  restricted sandbox denies, so verify `main()` with `tests/test_startup.py` instead of a live
  reload process.
- `--no-cache` for ruff: the `.ruff_cache` directory may be read-only (the linter then fails to
  create a temp file and reports exit code 1 despite "All checks passed").
- Tests create their own `.test-tmp/` tree because the system temp directory may be read-only;
  `pytest-cacheprovider` is disabled for the same reason.
- If `uv` fails with `Could not acquire lock`, set `UV_CACHE_DIR=.uv-cache`.

## Code Style — Zen of Python
- Beautiful is better than ugly.
- Explicit is better than implicit.
- Simple is better than complex.
- Readability counts.
- Errors should never pass silently.

Typing: annotate all public functions and models; prefer `str | None` over `Optional[str]`.
Domain errors go to `errors.py`, not bare `Exception`. Comments must be brief.

## Architecture Assessment (Before Any Change)
1. **Does this change fit the current architecture?** If yes, proceed.
2. **If no, can the architecture adapt slightly?** A small refactor is OK. State what and why.
3. **If a large architectural change is needed,** stop and ask the user first.

**Do not** silently reshape the architecture for one feature, move logic between layers, or edit
files outside the scope of the request.
