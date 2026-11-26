# Tasks

## 1. Ошибка и схемы

- [ ] 1.1 Добавить `EmptyTestError(DomainError)` в `errors.py` с маппингом `400`; проверить `python -m pytest tests/api/test_errors.py -q`
- [ ] 1.2 Перенести `TestOut`, `QuestionOut`, `ClosedOptionOut`, `RubricOut` в `schemas/test.py`, добавить в `TestOut` поля `material_id` и `created_at`, поправить импорты в `schemas/material.py` и `routers/material.py`; проверить `python -m pytest tests/api/test_materials.py tests/api/test_generation_action.py -q`, ответ карточки содержит `material_id` и `created_at`
- [ ] 1.3 Добавить `TestSummaryOut`, `TestListOut`, `TestUpdateRequest` (`title` 1..255, `extra="forbid"`); проверить `python -c "from testlab.schemas.test import TestUpdateRequest as T; T(title='x'); T(title='x', generation_params={})"` падает на `ValidationError`

## 2. Репозиторий

- [ ] 2.1 Добавить `get_by_id_and_teacher(test_id, teacher_id)` с загрузкой вопросов, вариантов и рубрик; проверить тестом в `tests/repositories/test_test_repository.py`: свой тест приходит с вопросами, чужой — `None`
- [ ] 2.2 Добавить `list_by_teacher(teacher_id, material_id, status, limit, offset)` с `total`, сортировкой `created_at desc, id desc` и `options(lazyload(Test.questions))`; проверить тестом: фильтры по материалу и статусу, пагинация, вопросы остаются незагруженными (`"questions" in inspect(test).unloaded`)
- [ ] 2.3 Добавить `get_active_by_material` (`draft`/`published`) и `get_latest_by_material` (любой статус); проверить тестом: архивный тест не попадает в активный, но попадает в последний
- [ ] 2.4 Добавить `delete(test)` с `flush`; проверить тестом, что удаление уносит вопросы, варианты и рубрики (каскад) и не трогает материал
- [ ] 2.5 Удалить `get_by_material` и перевести вызывающие места в `services/test.py` и `services/material.py` на новые методы; проверить, что ссылок на старый метод не осталось (`grep`), и `python -m pytest tests/services tests/repositories -q`

## 3. Сервис

- [ ] 3.1 Добавить приватные `_require_test`, `_require_draft`, `_require_published`; проверить тестами в `tests/services/test_test_service.py`: чужой тест → `NotFoundError`, неверный статус → `ConflictError`
- [ ] 3.2 Реализовать `list_tests` и `get_test`; проверить тестами: фильтры прокинуты в репозиторий, чужой тест → `NotFoundError`
- [ ] 3.3 Реализовать `update_title` (только `title`, только `draft`); проверить тестами: `draft` меняется, `published`/`archived` дают `ConflictError`, чужой — `NotFoundError`
- [ ] 3.4 Реализовать `publish` (проверка наличия вопросов) и `archive`; проверить тестами: публикация без вопросов → `EmptyTestError`, повторная публикация и архивирование черновика → `ConflictError`
- [ ] 3.5 Реализовать `delete_test` без проверки статуса; проверить тестами: удаляется `draft`, `published` и `archived`, после удаления `get_test` даёт `NotFoundError`
- [ ] 3.6 Вынести общие `_generate_questions(text, counts)` и переиспользовать `_build_questions`/`_generation_params` в `regenerate`: замена вопросов целиком, `title` не меняется, `order_index` по фактическому составу из `generation_params`; проверить тестами: успешная замена, `LLMError` сохраняет прежние вопросы, `404` на потерянный файл материала, `ConflictError` для `published`
- [ ] 3.7 Перевести `generate_for_material` на `get_active_by_material`; проверить тестом: материал с архивным тестом получает `201`, материал с `draft` — `409`

## 4. Роутер и API

- [ ] 4.1 Добавить в `routers/test.py` второй роутер `prefix="/tests"` с обработчиками `GET ""`, `GET "/{test_id}"`, `PATCH`, `POST "/{test_id}/publish"`, `POST "/{test_id}/archive"`, `DELETE`, `POST "/{test_id}/generate"`; зарегистрировать в `create_app()`; проверить `python -m pytest tests/test_startup.py -q` и что `GET /tests` появляется в `app.openapi()`
- [ ] 4.2 Написать `tests/api/test_tests.py`: список (пагинация, фильтры `material_id`/`status`, `422` на невалидные параметры, пустой список, отсутствие `questions` в элементе, `401`/`403`)
- [ ] 4.3 Добавить в `tests/api/test_tests.py` сценарии карточки, `PATCH`, `publish`, `archive`, `DELETE`: `404` на чужой тест, `409` на неверный статус, `400` на публикацию без вопросов, удаление в любом статусе
- [ ] 4.4 Добавить в `tests/api/test_tests.py` сценарии `POST /tests/{test_id}/generate`: `200` с новыми вопросами, `502` при сбое модели с сохранением прежних вопросов, `404` на чужой тест
- [ ] 4.5 Дополнить `tests/api/test_generation_action.py` сценарием «архивный тест не блокирует создание нового»; проверить `python -m pytest tests/api -q`
- [ ] 4.6 Обновить `docs/API.md`: раздел 4 как реализованный контракт (эндпоинты, коды, синхронный `200` у `generate`, удаление в любом статусе, `TestOut` с `material_id`/`created_at`); проверить, что в разделе не осталось пометки «не реализовано (план)» и что коды совпадают с тестами

## 5. Интеграция

- [ ] 5.1 Прогнать `python -m pytest -q -p no:cacheprovider` и `python -m ruff check . --no-cache`; оба должны завершиться успешно
- [ ] 5.2 Обновить `AGENTS.md` (состав `routers/test.py`, `services/test.py`, `repositories/test.py`, `schemas/test.py`, `errors.py`); проверить, что описание слоёв совпадает с кодом
- [ ] 5.3 Ручной прогон: создать тест по материалу → `PATCH title` → `generate` → `publish` → `PATCH` и `generate` (`409`) → `archive` → `DELETE` (`204`) → карточка материала `test: null` → повторное создание теста (`201`)

## Workflow follow-up

- После реализации заархивировать change (`/openspec-archive-change tests-lifecycle-endpoints`), синхронизировав delta-спеки с main-спеками.
