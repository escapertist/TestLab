# Proposal

## Why

Приложение сейчас не запускается: `__main__.py` импортирует отсутствующий модуль `testlab.routers.user_me`. Параллельно границы слоёв протекают в 10+ точках — репозиторий зависит от LLM-DTO, авторизация живёт в DI-модуле, валидация загрузки — в роутере, работа с диском — в сервисе, — а единой транзакции нет: падение на втором коммите оставляет материал без теста и PDF на диске. Блок «Материалы (teacher)» реализован на четверть: есть только `POST /materials`.

## What Changes

- **Устранение блокера старта**: убрать импорт несуществующего `testlab.routers.user_me`; `/auth/me` остаётся единственным маршрутом в `routers/user.py`; исправить entrypoint `testlab = "testlab.__main__:app"` (объект вместо callable); удалить шаблонный `main()` из `__init__.py`; `dispose()` движка перенести из старта в остановку lifespan (движок больше не пересоздаётся после `init_db`).
- **Перенос кода по слоям** (детали — в design.md):
  - доменные типы генерации (`GeneratedTest`, `GeneratedQuestion`, `GeneratedOption`, `GeneratedRubric`) — из `llm.py` в `domain/test_generation.py`;
  - перечисления (`UserRole`, `TestStatus`, `QuestionType`, `QuestionSource`) — из `models/enums.py` в `domain/enums.py`, `models` и `schemas` импортируют их из домена;
  - PDF-парсинг и файловое хранилище — из `services/material.py` в `infrastructure/pdf.py` и `infrastructure/storage.py`;
  - разрешение токена в пользователя и проверка роли — из `dependencies/user.py` в `services/auth.py`, DI-модуль остаётся тонким и только маппит доменные ошибки в `401/403`;
  - валидация загрузки (тип, пустота, размер) — из `routers/material.py` в `MaterialService`; лимит размера переезжает в `uploads`-конфиг;
  - маппинг доменных DTO в ORM (`order_index`, `source`) — из `repositories/test.py` в сервис;
  - сборка ответа `MaterialCreateResponse` — из императивного перечисления полей в `model_validate`.
- **Единица работы**: `UnitOfWork` в слое репозиториев; репозитории делают `flush()` и не коммитят; `commit`/`rollback` — один раз в сервисе на use case; при сбое сохранения в БД загруженный файл удаляется (компенсация), при сбое записи файла БД не трогается.
- **LLM-адаптер**: полная валидация ответа модели (типы полей, `points` в диапазоне 1..5, ровно один правильный вариант, наличие рубрики), приведение ошибок парсинга к `LLMError` вместо `500`, поворот на 401 (сброс токена и один повтор), фактический состав теста — в `generation_params` вместо захардкоженных 5/2.
- **Реализация блока «Материалы (teacher)»**: `POST /materials`, `GET /materials?limit=&offset=`, `GET /materials/{material_id}`, `GET /materials/{material_id}/file`, `DELETE /materials/{material_id}` по контракту `docs/API.md` (коды `201/200/204/400/401/403/404/413/502`), доступ только к своим материалам, удаление вместе с файлом и связанными тестами.
- **Включение внешних ключей SQLite** (`PRAGMA foreign_keys=ON` на соединение): без этого `ON DELETE CASCADE` в SQLite не работает и удаление материала оставляет висячие тесты.
- **Синхронизация документации**: `docs/API.md` (реализованный блок, `/health` и `/users` помечены как нереализованные), `docs/er.md` (типы `JSON`/`FLOAT` вместо `jsonb`/`numeric`, фактическая nullable-ность), `AGENTS.md` (новые пакеты, `UnitOfWork`, конфиг загрузок), `README.md`.
- **BREAKING (внутреннее)**: `MaterialService` и `UserService` получают `UnitOfWork` вместо отдельных репозиториев; `testlab.llm.GeneratedTest` переезжает в `testlab.domain.test_generation`. Внешний HTTP-контракт существующих эндпоинтов не меняется.

## Capabilities

### New Capabilities

- `materials`: блок материалов преподавателя — загрузка PDF с генерацией теста, список с пагинацией, карточка, скачивание файла, удаление; владение и коды ошибок.
- `llm-test-generation`: гарантии состава сгенерированного теста (5 закрытых + 2 открытых, ровно один правильный вариант, рубрика у открытого, `points` 1..5), валидация ответа модели и отображение сбоев в `502`.
- `app-startup`: сборка FastAPI-приложения из роутеров, регистрация каждого маршрута один раз, инициализация схемы БД в lifespan и корректное закрытие пула соединений при остановке.

### Modified Capabilities

Нет — спецификаций в проекте ещё нет, поведение фиксируется впервые.

## Impact

- Код: `src/testlab/__main__.py`, `__init__.py`, `database.py`, `llm.py`, `routers/material.py`, `routers/user.py`, `services/material.py`, `services/user.py`, `repositories/*`, `dependencies/*`, `schemas/*`, `models/enums.py`, `config/app_config.py`; новые пакеты `domain/`, `infrastructure/`, `repositories/uow.py`, `services/auth.py`.
- HTTP: `POST /materials` (существующий, без смены контракта), новые `GET /materials`, `GET /materials/{id}`, `GET /materials/{id}/file`, `DELETE /materials/{id}`.
- Данные: новых таблиц и колонок нет; меняется поведение удаления (каскад через внешние ключи SQLite) и содержимое `tests.generation_params`.
- Конфиг: лимит размера загрузки переезжает в `AppConfig` (`UPLOADS_MAX_BYTES`, дефолт 10 МБ).
- Зависимости: новых пакетов нет; `ruff` остаётся, pytest и `tests/` добавляются как dev-группа (без тестов задачи не проверить).
- Документация: `docs/API.md`, `docs/er.md`, `AGENTS.md`, `README.md`.
