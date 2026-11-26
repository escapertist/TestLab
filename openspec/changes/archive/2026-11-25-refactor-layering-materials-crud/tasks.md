# Tasks

## 1. Восстановление запуска

- [x] 1.1 Убрать импорт `testlab.routers.user_me` из `__main__.py`, оставить `routers.user` и `routers.material` по одному включению; проверить: `python -c "from testlab.__main__ import app; print([r.path for r in app.routes])"` не падает и `/auth/me` в списке один раз
- [x] 1.2 Перенести `dispose()` в остановку lifespan (создание схемы на входе, закрытие пула на выходе); проверить: `python -m testlab` стартует, выполняет `POST /materials` после старта без ошибки закрытого пула, корректно останавливается по Ctrl+C
- [x] 1.3 Добавить `main()` в `__main__.py`, перевести `[project.scripts] testlab` на `testlab.__main__:main`, удалить шаблонный `main()` из `src/testlab/__init__.py`; проверить: `testlab` и `python -m testlab` поднимают сервер на `127.0.0.1:8000`

## 2. Каркас тестов

- [x] 2.1 Добавить dev-группу `pytest`/`pytest-asyncio` и `[tool.pytest.ini_options]` (`asyncio_mode = "auto"`), установить; проверить: `.\.venv\Scripts\python.exe -m pytest -q` запускается и не падает на сборке
- [x] 2.2 Написать `tests/conftest.py`: тестовая БД `sqlite+aiosqlite://` с `StaticPool`, переопределения `get_db`/`get_uow`/`get_llm_client`, `uploads_dir` из `tmp_path`; проверить: smoke-тест «`GET /auth/me` без токена → 401» проходит

## 3. Домен

- [x] 3.1 Вынести `UserRole`, `TestStatus`, `QuestionType`, `QuestionSource` в `domain/enums.py`, в `models/enums.py` оставить реэкспорт; проверить: тест импортирует перечисления из `testlab.domain.enums`, `pytest` зелёный, `ruff check` чист
- [x] 3.2 Реализовать `domain/test_generation.py`: DTO `GeneratedTest`/`GeneratedQuestion`/`GeneratedOption`/`GeneratedRubric` и `parse_generated_test(raw)` со снятием markdown-обёртки, проверками состава 5+2, закрытых/открытых вопросов, `points` 1..5, строгого `is_correct`; проверить: `tests/domain/test_test_generation.py` покрывает успех и каждый отказ из спеки `llm-test-generation`

## 4. Инфраструктура

- [x] 4.1 Добавить `uploads_max_bytes` в `AppConfig` (дефолт 10 МБ, переопределение через env); проверить: тест `settings.uploads_max_bytes == 10 * 1024 * 1024` и переопределение через переменную окружения
- [x] 4.2 Реализовать `infrastructure/pdf.py::extract_text(content) -> str` с ошибкой `MaterialValidationError` на битом PDF и отсутствии текстового слоя; проверить: тесты на фикстуре PDF с текстом (возвращает текст), на пустой странице (ошибка) и на мусорных байтах (ошибка)
- [x] 4.3 Реализовать `infrastructure/storage.py`: протокол `FileStorage` и `LocalFileStorage` (`save`, `delete`, нормализация суффикса), путь — из `uploads_dir`; проверить: тесты «файл создан по возвращённому пути», «delete удаляет», «delete отсутствующего файла не падает», «суффикс не `.pdf` заменяется на `.pdf`»
- [x] 4.4 Перенести транспорт GigaChat в `infrastructure/llm.py`: клиент принимает `settings` и `httpx.AsyncBaseTransport`, промпт и усечение входа внутри, ретрай на `401` (сброс токена + один повтор); проверить: тесты на `MockTransport` — успех, `401`→повтор→успех, два `401` → `LLMError`, таймаут → `LLMError` без токенов в тексте

## 5. Слой данных

- [x] 5.1 Ввести `repositories/uow.py::UnitOfWork` (репозитории + `commit`/`rollback`), из репозиториев убрать `commit`, оставить `flush`; проверить: тесты «commit сохраняет», «rollback отбрасывает», и что ни один модуль `repositories/*` не вызывает `session.commit`
- [x] 5.2 Включить `PRAGMA foreign_keys=ON` слушателем `connect` только для SQLite; проверить: тест «удаление материала удаляет связанные тест, вопросы, варианты и рубрики»
- [x] 5.3 Переписать `MaterialRepository` (`create`, `list_by_teacher`, `get_by_id_and_teacher`, `delete`) и `TestRepository.create_with_questions(test, questions: list[Question])` на ORM-объекты вместо LLM-DTO; проверить: тесты репозиториев на пагинацию, изоляцию по `teacher_id` и порядок вопросов

## 6. Доменные ошибки и маппинг

- [x] 6.1 Заменить `exceptions.py` на `errors.py`: `NotFoundError`, `PermissionDeniedError`, `InvalidTokenError`, `MaterialValidationError`, `UploadTooLargeError`, `PersistenceError`, `LLMResponseError(LLMError)` и `register_exception_handlers(app)` по таблице маппинга из `design.md`; проверить: тест на каждый класс исключения — ожидаемый HTTP-код и `{"detail": ...}`
- [x] 6.2 Убрать `try/except` из роутеров и подключить хендлеры в `create_app()`; проверить: тест «`UserAlreadyExistsError` из сервиса → 400», «`LLMError` → 502», «`PersistenceError` → 500» без обработки в роутере

## 7. Сервисы

- [x] 7.1 Реализовать `services/auth.py::AuthService` (`authenticate`, `require_teacher`) и `dependencies/auth.py` (`get_auth_service`, `get_current_user`, `get_current_teacher`, алиас `CurrentUser`), перенести разбор токена из DI; проверить: тесты API — нет токена → 401, неизвестный id → 401, `student` на материалах → 403, `/auth/me` → 200 своему пользователю
- [x] 7.2 Перевести `services/user.py` на `UnitOfWork`: `register` (гонка по username → `UserAlreadyExistsError` из `IntegrityError`), `login`, выдача токена-заглушки сервисом; проверить: тесты «регистрация», «дубль username → 400», «неверный пароль → 401», «выданный токен проходит `authenticate`»
- [x] 7.3 Реализовать `services/material.py` на `UnitOfWork` + `FileStorage` + клиент модели: валидация загрузки (тип, пустота, лимит, текстовый слой), сборка ORM-вопросов из DTO, `generation_params` по факту, компенсация файла при сбое коммита; проверить: тесты «успех», «сбой модели → нет материала, теста и файла», «сбой коммита → файл удалён, ошибка 500», «чужой материал → `NotFoundError`»

## 8. HTTP-слой и схемы

- [x] 8.1 Добавить `schemas/common.py::UtcDatetime` (naive трактуется как UTC, сериализация `...Z`), перевести модели на `DateTime(timezone=True)` и `nullable=False`; проверить: тест «`register`, `login` и `/auth/me` отдают одинаковый формат времени с суффиксом `Z`»
- [x] 8.2 Реализовать в `routers/material.py` пять эндпоинтов и схемы `MaterialListOut`/`MaterialDetailOut`; проверить: `tests/api/test_materials.py` покрывает `201`, `400`, `413`, `403`, `401`, список с пагинацией (`items`/`total`, `422` на невалидные `limit`/`offset`), карточку, скачивание (`application/pdf`, `Content-Disposition`), `204` и `404` при удалении и для чужих материалов
- [x] 8.3 Привести `routers/user.py` к тонкому виду: без `try/except` и без ручной сборки токена, `me` — единственный маршрут `/auth/me`; проверить: тесты auth зелёные, в `app.routes` нет дублей пути с методом

## 9. Документация

- [x] 9.1 Обновить `docs/API.md`: реализованные пять эндпоинтов материалов, формат списка и карточки, коды ошибок; `/health` и `/users` пометить как нереализованные; проверить: список путей в документе совпадает с `app.routes` (сверка вручную или скриптом в тесте)
- [x] 9.2 Обновить `docs/er.md` и `docs/sql_scripts.sql` под фактические типы/`nullable`/дефолты моделей, дописать `AGENTS.md` (новые пакеты `domain`/`infrastructure`, `UnitOfWork`, `uploads_max_bytes`, entrypoint `main`) и `README.md`; проверить: `AGENTS.md` перечисляет те же пути, что существуют в `src/testlab`

## 10. Интеграционные проверки

- [x] 10.1 Добавить `tests/test_imports.py`: AST-разбор импортов по таблице правил из `design.md` (routers не видят `models`/`repositories`, сервисы не видят `fastapi`/`sqlalchemy`, домен не видит `models`); проверить: тест падает при добавлении запрещённого импорта и зелёный на итоговом коде
- [x] 10.2 Прогнать полный набор: `.\.venv\Scripts\python.exe -m pytest -q`, `.\.venv\Scripts\python.exe -m ruff check .`, `testlab-init-db --reset`, ручной прогон `POST /materials` → `GET /materials` → `GET /materials/{id}` → `GET /materials/{id}/file` → `DELETE /materials/{id}` на живом сервере; проверить: тесты и линтер чистые, все пять вызовов дают ожидаемые коды

## Workflow follow-up

- Проверить изменения ревью и архивировать change после подтверждения.
