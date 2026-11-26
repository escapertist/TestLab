# Tasks

## 1. Хранилище и доменные ошибки

- [x] 1.1 Добавить `read` в протокол `FileStorage` и `LocalFileStorage` (чтение в потоке, `NotFoundError` при отсутствии файла); проверить: тесты «read возвращает байты» и «read отсутствующего файла → `NotFoundError`» в `tests/infrastructure/test_storage.py` проходят
- [x] 1.2 Добавить `ConflictError` в `errors.py` и маппинг `409`; проверить: тест «`ConflictError` из сервиса → `409` с `detail`» в `tests/api/test_errors.py` проходит

## 2. Загрузка без генерации

- [x] 2.1 Переписать `MaterialService` в `upload_pdf(teacher_id, title, filename, content_type, content) -> Material`: убрать зависимость от LLM, оставить валидацию, извлечение текста как проверку, запись файла и компенсацию при сбое коммита; проверить: `tests/services/test_material_service.py` — успех, сбой коммита удаляет файл, фейк модели с ошибкой не влияет на загрузку
- [x] 2.2 Роутер `POST /materials` возвращает `MaterialOut` (`201`, без `test`), схема `MaterialCreateResponse` удалена; проверить: `tests/api/test_materials.py` — `201`, в теле нет `test`, коды `400/413/401/403` на месте
- [x] 2.3 Поправить `tests/conftest.py` и хелперы загрузки под новый ответ; проверить: `.\.venv\Scripts\python.exe -m pytest tests -q -p no:cacheprovider` зелёный

## 3. Создание теста отдельным действием

- [x] 3.1 Реализовать `services/test.py::TestService.generate_for_material`: владение материалом, `409` при существующем тесте, чтение файла через `FileStorage.read`, извлечение текста, вызов модели, сборка вопросов и `generation_params`, один коммит; проверить: `tests/services/test_test_service.py` — успех, `ConflictError`, `NotFoundError` (чужой материал и потерянный файл), `PersistenceError` при сбое коммита
- [x] 3.2 Добавить `dependencies/test.py::get_test_service` и `routers/test.py` с `POST /materials/{material_id}/tests` (`201`, опциональный `title`, тег `tests`), зарегистрировать роутер в `create_app()`; проверить: `tests/api/test_generation_action.py` — `201` с 7 вопросами, `title` из тела, `403`, `401`; `tests/test_startup.py` видит маршрут один раз. Файл назван `test_generation_action.py`, а не `test_test_generation.py`: базовое имя совпало бы с `tests/domain/test_test_generation.py` и pytest падал бы на коллизии импорта
- [x] 3.3 Проверить связку с карточкой: до генерации `test: null` и файл скачивается, после — тест с вопросами, повторная генерация `409`, сбой модели `502` без теста; проверить: соответствующие сценарии в `tests/api/test_generation_action.py` и `tests/api/test_materials.py` проходят

## 4. Документация

- [x] 4.1 Обновить `docs/API.md`: загрузка без `test`, новое действие `POST /materials/{id}/tests`, коды `201/400/404/409/502`, порядок реализации; проверить: `tests/test_startup.py::test_api_docs_cover_implemented_routes` дополнен новым путём и проходит
- [x] 4.2 Обновить `AGENTS.md` (роутеры/сервисы/провайдеры, `ConflictError`, `FileStorage.read`) и `README.md` («что уже работает»); проверить: перечисленные в `AGENTS.md` пути существуют в `src/testlab`

## 5. Интеграционная проверка

- [x] 5.1 Прогнать `.\.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider`, `.\.venv\Scripts\python.exe -m ruff check . --no-cache` и живой сценарий: загрузка → карточка (`test: null`) → генерация → карточка с тестом → повторная генерация (`409`); проверить: тесты и линтер чистые, коды совпадают с `docs/API.md`

Живой сценарий прогнан на поднятом uvicorn (`127.0.0.1:8010`, временные `DB_URL`/`UPLOADS_DIR`):
с пустым `GIGACHAT_CREDENTIALS` подтверждены `201` загрузки без `test`, `test: null` в карточке,
скачивание файла, `401` без токена и `502` на генерации; ветка `201` с 7 вопросами и повторный `409`
проверены тем же сценарием через `TestClient` с подменённым LLM (`get_llm_client`).

## Workflow follow-up

- Архивировать `refactor-layering-materials-crud` до архивации этого change: его спецификации — база для дельт `MODIFIED`.
- Архивировать этот change после ревью.
