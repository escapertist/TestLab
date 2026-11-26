# Design

## Context

См. `proposal.md` — Why. Существующий код: `routers → services → repositories → models`, `schemas` для ввода-вывода, `dependencies` для DI, `llm.py`/`database.py`/`security.py` в корне пакета. Фактическое состояние нарушает этот граф:

- `repositories/test.py` принимает DTO из `llm.py` и сам расставляет `order_index`/`source`;
- `dependencies/user.py` содержит авторизацию поверх репозитория, минуя сервис;
- `routers/material.py` валидирует файл и импортирует константу сервиса и ORM-модель;
- `services/material.py` пишет файлы и парсит PDF;
- каждый репозиторий коммитит сам, поэтому use case не атомарен;
- `schemas` и `llm` зависят от `models.enums`;
- `__main__.py` импортирует отсутствующий `routers.user_me` — приложение не стартует.

Ограничения: Python 3.15, FastAPI, SQLAlchemy 2 async + aiosqlite (по умолчанию), `uv`. Миграций нет — схема создаётся `create_all`. Внешний HTTP-контракт существующих эндпоинтов не меняется.

## Goals / Non-Goals

**Goals:**

- Восстановить однонаправленный граф зависимостей: `routers → services → repositories → models`, `schemas` и `domain` не зависят от `models`/инфраструктуры.
- Сделать каждый use case одной транзакцией с компенсацией побочных эффектов (файл на диске).
- Реализовать блок «Материалы (teacher)» целиком по контракту `docs/API.md`.
- Сделать починку проверяемой: pytest-тесты на доменные правила, сервис и HTTP.

**Non-Goals:**

- JWT, проверка срока токена, роли `admin`.
- CRUD тестов/вопросов, назначения, прохождение, проверка преподавателем.
- Alembic и миграции; `create_all` остаётся.
- `GET /health`, `GET /users` — только помечаются в документации как нереализованные.
- Кэш, фоновые задачи (Celery/очереди), стриминг файлов.

## Decisions

### 1. Целевая структура пакетов

```text
testlab/
  __main__.py            create_app(), lifespan, main()
  errors.py              доменные исключения + регистрация HTTP-хендлеров
  database.py            Base, engine, session maker, get_db, init_db
  security.py            Argon2 (хеширование паролей)
  domain/
    enums.py             UserRole, TestStatus, QuestionType, QuestionSource
    test_generation.py   GeneratedTest/Question/Option/Rubric + parse_generated_test()
  infrastructure/
    llm.py               промпт, HTTP-клиент GigaChat, ретрай на 401
    pdf.py               extract_text(content) -> str
    storage.py           FileStorage (Protocol) + LocalFileStorage
  routers/               user.py, material.py
  schemas/               common.py (UtcDatetime), user.py, material.py
  services/              user.py, auth.py, material.py
  repositories/          uow.py, user.py, material.py, test.py
  models/                user.py, material.py, test.py, __init__.py
  dependencies/          user.py, auth.py, material.py
  config/                base_config.py, db_config.py, llm_config.py, app_config.py
```

Правила, которые проверяет ревью и тесты импортов:

| Модуль | Может импортировать | Запрещено |
|---|---|---|
| `routers/*` | `schemas`, `services`, `dependencies`, `errors` | `models`, `repositories`, `database`, `infrastructure` |
| `services/*` | `domain`, `models`, `repositories`, `exceptions`, `infrastructure` (через протоколы) | `sqlalchemy`, `fastapi`, `httpx` |
| `repositories/*` | `models`, `sqlalchemy` | `services`, `llm`, `domain`-DTO |
| `domain/*` | stdlib | `models`, `sqlalchemy`, `fastapi`, `httpx` |
| `schemas/*` | `domain` | `models`, `repositories` |
| `infrastructure/*` | `domain`, `config`, `errors` | `models`, `services`, `repositories` |
| `dependencies/*` | все слои — это композиционный корень | бизнес-логика сверх выбора реализации и проверки роли |

`models.enums` остаётся как реэкспорт из `domain.enums`, чтобы не ломать существующие импорты в один шаг; новые импорты — только из домена.

Альтернатива: оставить `enums` в `models` и разрешить `schemas → models`. Отклонено: `schemas` — контракт ввода-вывода, зависимость от ORM-слоя тянет `sqlalchemy` в ответы и мешает вынести домен позже.

### 2. UnitOfWork вместо commit в репозиториях

`repositories/uow.py`:

```python
class UnitOfWork:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.users = UserRepository(session)
        self.materials = MaterialRepository(session)
        self.tests = TestRepository(session)

    async def commit(self) -> None: ...
    async def rollback(self) -> None: ...
```

- Репозитории только `add`/`flush`/`select`; `commit` вызывается один раз в сервисе.
- Провайдер `get_uow(db=Depends(get_db))`; `get_db` остаётся один на запрос, поэтому `get_current_user` и сервис материала работают с одной сессией.
- `__aexit__`/`close` сессии при исключении даёт откат; явный `rollback()` вызывается в `except` сервиса до `commit`.

Альтернатива: `commit()` в каждом методе репозитория (текущее состояние) — отклонено, потому что use case «материал + тест + файл» перестаёт быть атомарным.

### 3. Компенсация файлового эффекта

Порядок в `MaterialService.create_from_pdf`:

```text
text = pdf.extract_text(content)          # MaterialValidationError -> 400
test = await llm.generate_test(text)      # LLMError -> 502
file_path = await storage.save(content, suffix)   # PersistenceError -> 500
try:
    uow.add(material); uow.add(test); await uow.commit()
except Exception:
    await uow.rollback()
    await storage.delete(file_path)       # best-effort, ошибка логируется
    raise PersistenceError(...)
```

Файл пишется до коммита: при сбое БД он удаляется. Обратный порядок (коммит, потом файл) оставлял бы материал без файла и 500 после уже успешного ответа.

`LocalFileStorage.save` хранит имена `uuid4().hex + suffix`; `suffix` берётся из имени файла и допускается только `.pdf` (иначе `.pdf`). Путь — `settings.uploads_dir` (абсолютный путь вычисляется в инфраструктуре, в БД пишется абсолютный путь).

### 4. Удаление: сначала БД, потом файл

`DELETE /materials/{id}`: проверить владение → `uow.materials.delete(material)` → `commit` (каскад FK удаляет тесты/вопросы/варианты/рубрики) → `storage.delete(file_path)` best-effort. Если файла нет — это не ошибка (`404` только при отсутствии записи). Ошибка удаления файла логируется, ответ остаётся `204`: откатывать уже удалённую запись ради файла нельзя, а повтор на клиенте получит `404`.

### 5. Внешние ключи SQLite

`ON DELETE CASCADE` в SQLite не работает без `PRAGMA foreign_keys = ON`, поэтому в `database.py` регистрируется слушатель события `begin` на `engine.sync_engine`, который выполняет `PRAGMA foreign_keys=ON`. Событие `connect` не подходит: внутри него адаптер aiosqlite ещё не даёт синхронно выполнить SQL (курсор возвращает корутину), а PRAGMA не действует внутри уже начатой транзакции. Для `postgresql+asyncpg` слушатель ничего не делает (FK включены всегда). Тот же слушатель ставится тестовому движку.

Альтернатива: явное удаление тестов в репозитории перед материалом. Отклонено: дублирует ограничение БД и расходится со схемой при появлении новых дочерних таблиц.

### 6. Владение и 404 вместо 403

Репозиторий фильтрует по `teacher_id` в SQL (`get_by_id_and_teacher`, `list_by_teacher`), поэтому «чужой» объект неотличим от отсутствующего. Сервис бросает `NotFoundError`; HTTP-хендлер маппит его в `404`. `403` остаётся только для роли (`get_current_teacher`).

### 7. Авторизация — сервис, а DI только собирает

`services/auth.py`:

```python
class AuthService:
    async def authenticate(self, token: str) -> User      # InvalidTokenError
    def require_teacher(self, user: User) -> User         # PermissionDeniedError
```

`dependencies/auth.py` даёт `get_auth_service`, `get_current_user`, `get_current_teacher`; исключения маппятся централизованно. Разбор `UUID`, поиск пользователя и проверка роли уходят из DI-модуля.

### 8. Централизованный маппинг доменных ошибок

`errors.py` (переименованный `exceptions.py`) содержит исключения и `register_exception_handlers(app)`:

| Исключение | HTTP |
|---|---|
| `InvalidCredentialsError` | 401 |
| `InvalidTokenError` | 401 |
| `PermissionDeniedError` | 403 |
| `NotFoundError` | 404 |
| `UserAlreadyExistsError` | 400 |
| `MaterialValidationError` (не PDF, пусто, нет текста) | 400 |
| `UploadTooLargeError` | 413 |
| `LLMError` (включая `LLMResponseError`) | 502 |
| `PersistenceError` | 500 |
| `IntegrityError` из SQLAlchemy при гонке username | 400 |

Роутеры перестают писать `try/except` и просто вызывают сервис; формат ошибки остаётся FastAPI-совместимым (`{"detail": "..."}`).

Альтернатива: `try/except` в каждом роутере (как сейчас) — отклонено: одинаковые маппинги дублируются, а `MaterialProcessingError → 400` уже ошибочно отправляет серверные сбои в 400.

### 9. Валидация загрузки — в сервисе

Роутер читает `UploadFile` в `bytes` и передаёт `content`, `filename`, `content_type` в `MaterialService.create_from_pdf`. Сервис проверяет: расширение/тип (`.pdf`), непустоту, лимит `settings.uploads_max_bytes` (новое поле `AppConfig`, дефолт 10 МБ), наличие текстового слоя. Роутер больше не импортирует `MAX_PDF_SIZE`: лимит читается сервисом из конфига. Через границу слоёв проходит один тип — объект пользователя. Чтобы роутер не импортировал `models`, `dependencies/auth.py` объявляет алиас `CurrentUser = Annotated[User, Depends(get_current_user)]` (импорт `models` остаётся только в композиционном корне), а роутер пишет `user: CurrentUser`. Проверка импортов в тесте это фиксирует.

### 10. LLM: транспорт и правила разделены

- `infrastructure/llm.py`: OAuth, HTTP, промпт, ретрай на `401` (сброс токена + один повтор), усечение входа; возвращает `GeneratedTest`.
- `domain/test_generation.py`: `parse_generated_test(raw)` — снятие markdown-обёртки, разбор JSON, проверки состава (5/2), закрытых/открытых вопросов, `points` 1..5; бросает `LLMResponseError`.
- `GigaChatClient` создаётся провайдером `get_llm_client()` и внедряется в `MaterialService`; дефолта-синглтона в сигнатуре нет.
- `generation_params` собирает сервис: `{"model", "closed_count", "open_count", "text_chars", "text_truncated"}` — фактически отправленное.

Строгая проверка «ровно 5 + 2» выбрана, потому что контракт API и `generation_params` уже это обещают; частичный тест пришлось бы отдельно описывать.

### 11. Сериализация времени

`models` объявляют `DateTime(timezone=True)` и `nullable=False`; `schemas/common.py::UtcDatetime` — `Annotated[datetime, PlainSerializer(...)]`, который naive-значение трактует как UTC и печатает `...Z`. Это убирает расхождение между `register` (aware-объект) и `login`/`me` (naive из SQLite) и приводит ответ к обещанному в `docs/API.md` ISO 8601 UTC.

### 12. Старт и остановка

`__main__.py`: `create_app()` собирает роутеры `routers.user` и `routers.material` (по одному разу), `lifespan` создаёт схему на входе и закрывает пул на выходе:

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db(async_engine)
    yield
    await async_engine.dispose()
```

`main()` запускает uvicorn; `[project.scripts] testlab = "testlab.__main__:main"`; `python -m testlab` вызывает тот же `main()`.

### 13. Тесты

- `pytest` + `pytest-asyncio` + `httpx.ASGITransport` в dev-группе `pyproject.toml`.
- `tests/conftest.py`: тестовая БД `sqlite+aiosqlite://` с `StaticPool`, фикстуры переопределяют `get_db`/`get_uow`, `get_llm_client` (fake, отдаёт заготовленный JSON), `uploads_dir` (tmp_path).
- Уровни: `tests/domain/` — правила парсинга и состава; `tests/services/` — атомарность, компенсация файла, удаление; `tests/api/` — коды ответов, владение, 404 на чужие, пагинация.
- Дополнительно `tests/test_imports.py`: статический разбор AST по таблице правил из решения 1 — ревью слоёв автоматизируется.

## Risks / Trade-offs

- [Строгий контракт 5+2 даёт больше `502` на реальной модели] → считать ошибку явной, сообщение содержит причину; ослабление — отдельное изменение спеки, не тихая подмена.
- [Каскад зависит от `PRAGMA foreign_keys`] → слушатель на `connect` + API-тест «удаление материала убирает тест».
- [Перенос модулей ломает импорты у внешних потребителей пакета] → внутри проекта все импорты обновляются одним коммитом, `models.enums` остаётся реэкспортом, AGENTS.md дополняется новыми правилами; `ruff check` и тесты в задаче верификации.
- [Файл на диске может остаться, если удаление после коммита упало] → логирование; прибирать осиротевшие файлы планируется вместе с фоновой очисткой, не в этом изменении.
- [Компенсация файла не транзакционная: падение процесса между записью файла и коммитом оставит файл] → приемлемо для учебного сервиса, файл с уникальным именем не конфликтует; описано как известное ограничение.
- [Централизованные хендлеры меняют привычку «роутер маппит ошибки»] → AGENTS.md обновляется, тесты фиксируют коды.

## Migration Plan

1. Добавить `domain/`, `infrastructure/`, `repositories/uow.py`, `errors.py` рядом с текущим кодом.
2. Перевести `llm.py`/`services`/`repositories`/`dependencies`/`routers` на новые модули; `models.enums` — реэкспорт.
3. Включить `PRAGMA foreign_keys`, поправить `lifespan` и entrypoint.
4. Добавить эндпоинты блока материалов и тесты.
5. Обновить `docs/API.md`, `docs/er.md`, `AGENTS.md`, `README.md`.
6. Проверка: `pytest`, `ruff check .`, `python -m testlab`, ручной прогон `POST/GET/GET{id}/GET file/DELETE`.

Схема БД не меняется (новых таблиц и колонок нет), поэтому откат — revert коммита; данные, созданные новым кодом, старый код читает без изменений.
