# Design

## Context

См. `proposal.md` — Why. Текущее состояние: [`routers/test.py`](src/testlab/routers/test.py) содержит
единственный маршрут `POST /materials/{material_id}/tests` с `prefix="/materials"` и тегом `tests`;
[`services/test.py`](src/testlab/services/test.py) — один use case `generate_for_material`
(владение → `409` → `storage.read` → `extract_text` → `llm.generate_test` → один коммит), плюс
приватные `_build_questions` и `_generation_params`;
[`repositories/test.py`](src/testlab/repositories/test.py) умеет только `create_with_questions`,
`get_with_questions` и `get_by_material`; [`schemas/material.py`](src/testlab/schemas/material.py)
держит `TestOut`, `QuestionOut`, `ClosedOptionOut`, `RubricOut`; в [`errors.py`](src/testlab/errors.py)
уже есть `ConflictError → 409`, `NotFoundError → 404`, `LLMError → 502`, `PersistenceError → 500`.

Ограничения: схема БД не меняется — `tests.status` и `questions.source` уже есть, миграций и
`create_all`-трюков не нужно; `Test.questions` и `Question.options` объявлены с `lazy="selectin"`, поэтому
любая выборка теста тянет вопросы; владение материалом проверяется в SQL (`teacher_id`), и чужой объект
неотличим от отсутствующего.

Зависимость от `structured-llm-generation-check`: клиент GigaChat становится параметрическим (состав
из запроса, `with_structured_output`), поэтому перегенерация здесь опирается на `generation_params`.

## Goals / Non-Goals

**Goals:**

- Жизненный цикл теста живёт в одном сервисе и одном роутере, без дублирования правил статусов.
- Правило «опубликованный тест неизменяем» проверяется в одном месте и не размазывается по обработчикам.
- Генерация по материалу и перегенерация используют один код вызова модели и сборки вопросов.
- Список тестов не тянет вопросы из БД (иначе `limit=100` — это ~700 вопросов с вариантами).

**Non-Goals:**

- Редактирование вопросов (`POST/PATCH/DELETE /questions`, порядок) — отдельный change.
- Асинхронная генерация (`202`, статус `generating`, очередь) — очередь и воркер не появляются.
- Версионирование теста (`test_version`) и `409` при удалении теста с назначениями — до блока 6.
- Новые поля в `tests` (число вопросов, `updated_at`), мягкое удаление.

## Decisions

### 1. Второй роутер в существующем модуле

```python
# routers/test.py
router = APIRouter(prefix="/materials", tags=["tests"])        # существующий: POST /{material_id}/tests
tests_router = APIRouter(prefix="/tests", tags=["tests"])      # новый блок
```

`create_app()` включает оба. Альтернатива — отдельный `routers/test_lifecycle.py`: отклонена, модуль
`routers/` разложен по ресурсам (`user`, `material`, `test`), а не по фичам; тег `tests` оставляет
Swagger сгруппированным, и `tests/test_imports.py` не трогается.

### 2. `TestService` расширяется, а не дробится

Новые use cases — методы того же `TestService`: `list_tests`, `get_test`, `update_title`, `publish`,
`archive`, `delete_test`, `regenerate`. Альтернатива — `TestLifecycleService` рядом: отклонена, у него
те же зависимости (`uow`, `storage`, `llm`) и те же приватные хелперы генерации; два сервиса пришлось
бы связывать, а правило статусов дублировать.

### 3. Схемы теста переезжают в `schemas/test.py`

`TestOut`, `QuestionOut`, `ClosedOptionOut`, `RubricOut` переезжают из `schemas/material.py`, который
теперь импортирует `TestOut` для `MaterialDetailOut`. Зависимость односторонняя (материал → тест),
цикла нет. `TestOut` дополняется `material_id` и `created_at`. Новые: `TestSummaryOut` (элемент списка
без вопросов), `TestListOut` (`items`, `total`), `TestUpdateRequest`.

Альтернатива — оставить `TestOut` в `schemas/material.py` и импортировать оттуда: отклонена, тест —
не часть материала, и блоку вопросов тоже понадобятся эти схемы.

### 4. Репозиторий: явные методы вместо одного `get_by_material`

```python
async def get_by_id_and_teacher(test_id, teacher_id) -> Test | None     # с вопросами, владение в SQL
async def list_by_teacher(teacher_id, material_id, status, limit, offset) -> tuple[list[Test], int]
async def get_active_by_material(material_id) -> Test | None            # draft | published
async def get_latest_by_material(material_id) -> Test | None            # любой статус
async def delete(test) -> None                                          # + flush
```

`get_by_material` заменяется двумя методами, потому что у него стало два разных намерения: карточке
материала нужен последний тест в любом статусе, а проверке `409` — только активный. В
`list_by_teacher` запрос выполняется с `options(lazyload(Test.questions))`: `selectin` по умолчанию
превратил бы страницу списка в загрузку всех вопросов с вариантами. `total` считается отдельным
`func.count()` по тем же фильтрам — как в `MaterialRepository.list_by_teacher`.

### 5. Статусные правила — в сервисе, через два приватных помощника

```python
def _require_draft(test: Test) -> None:      # иначе ConflictError 409
def _require_published(test: Test) -> None:  # иначе ConflictError 409
```

| use case | проверка |
|---|---|
| `update_title` | `_require_draft` |
| `regenerate` | `_require_draft` |
| `publish` | `_require_draft` + наличие вопросов (`EmptyTestError` → `400`) |
| `archive` | `_require_published` |
| `delete_test` | нет проверки статуса |

Альтернатива — constraint в БД или триггер: триггер проверил бы переход статуса, но не «не менять
вопросы опубликованного», и всё равно потребовал бы маппинга ошибки в `409`. Правило принадлежит
домену, живёт в сервисе.

### 6. Публикация требует вопросов — новый `EmptyTestError`

В `errors.py` добавляется `EmptyTestError(DomainError) → 400`. Переиспользовать
`MaterialValidationError` нельзя: имя врёт, а `400` уже занят именно валидацией материала. Вопросы
нужны только для проверки «их вообще нет», поэтому связь `test.questions` уже загружена
(`lazy="selectin"`) и отдельный `COUNT` не нужен.

### 7. Перегенерация — одна транзакция, полная замена

```text
test     = _require_test(teacher_id, test_id)                 -> 404
_require_draft(test)                                          -> 409
material = uow.materials.get_by_id_and_teacher(test.material_id, teacher_id)  -> 404
content  = await storage.read(material.file_path)             -> NotFoundError 404
text     = extract_text(content)                              -> MaterialValidationError 400
counts    = _shape_from(test.generation_params)                # closed/open/options_count, fallback 5/2/4
generated = await llm.generate_test(text, **counts)            -> LLMError 502
test.questions.clear(); test.questions.extend(_build_questions(generated.questions))
test.generation_params = _generation_params(generated, text)   # title не трогаем
uow.commit()                                                   -> except: rollback -> PersistenceError 500
```

`clear()` + `extend` на загруженной связи удаляет прежние строки через `delete-orphan` и вставляет
новые в одной транзакции — при сбое модели или коммита прежние вопросы остаются. Отдельного метода
репозитория не нужно. Материал берётся существующим `get_by_id_and_teacher`: владение уже доказано
тестом, но повторная проверка бесплатна и не требует нового метода.

Состав для перегенерации берётся из `test.generation_params` (запрошенные при создании
`closed_count`/`open_count`/`options_count`); для тестов, созданных до параметризации, — fallback
`5/2/4`.

```text
POST /tests/{id}/generate            -> 200, тест с новыми вопросами
```

### 8. Синхронный `200` вместо `202`

`docs/API.md:232` описывает `202 {"status": "started"}`, но это требует очереди, воркера и статуса
`generating`, которых нет; сам документ (`:238`) разрешает синхронную учебную реализацию. Принято
`200` с телом теста — как у `POST /materials/{id}/tests`, где 60-секундный таймаут модели уже
держит соединение.

### 9. `generation_params` не редактируются клиентом

`PATCH` принимает только `title`; `TestUpdateRequest` объявлен с `extra="forbid"`, поэтому
`generation_params` в теле даёт `422`, а не молчаливое игнорирование. Причина: это происхождение
данных (`model`, `text_chars`, `text_truncated`), их считает сервис; клиентская правка сделала бы
поле недостоверным, а `/generate` берёт состав из `generation_params`.

### 10. Список без количества вопросов

`TestSummaryOut`: `id`, `material_id`, `title`, `status`, `created_at`. `questions_count` не
добавляем — это второй запрос на страницу, а количество видно в карточке. Список и карточка — две
разные схемы, и это осознанно.

### 11. `409` при создании теста смотрит только на активные

`generate_for_material` переключается с `get_by_material` на `get_active_by_material`, поэтому
архивный тест не блокирует новый. Это делает возможным версионирование без колонки `version`:
`archived` — история, `draft`/`published` — не больше одного активного теста на материал.

## Risks / Trade-offs

- [Удаление опубликованного теста станет опасным, когда появятся назначения (`docs/er.md:15`)] →
  сейчас `assignments`/`results` не существуют, каскад никого не задевает; в блоке 6 удаление теста с
  назначениями станет `409`. Записано как известное ограничение, а не как забытая дыра.
- [У материала может быть несколько тестов] → карточка отдаёт последний по `created_at`, список с
  фильтром `material_id` показывает историю; клиент, читавший «единственный» тест из карточки,
  продолжает работать.
- [Элемент списка и карточка различаются по форме] → за вопросами клиент идёт в `GET /tests/{id}`;
  две схемы дешевле, чем загрузка вопросов на страницу списка.
- [Публикация без вопросов снаружи пока недостижима: генерация всегда даёт вопросы] → правило
  оставлено, потому что блок 5 позволит удалять вопросы, и тогда `400` станет реальной веткой.
- [Неатомарная проверка «активного теста нет» при создании] → та же гонка, что и раньше; жёсткая
  защита потребовала бы уникального частичного индекса по `(material_id)` для активных статусов —
  возможно отдельным изменением.

## Migration Plan

Схема БД не меняется, данные не мигрируют, откат — revert коммита.

1. `errors.py`: `EmptyTestError → 400`.
2. `schemas/test.py`: переезд `TestOut` и вложенных схем, новые `TestSummaryOut`, `TestListOut`,
   `TestUpdateRequest`; обновить импорты в `schemas/material.py` и `routers/material.py`.
3. `repositories/test.py`: `get_by_id_and_teacher`, `list_by_teacher`, `get_active_by_material`,
   `get_latest_by_material`, `delete`; `get_by_material` удаляется, вызывающие места обновляются.
4. `services/test.py`: новые use cases и общие хелперы генерации; `generate_for_material` переходит
   на `get_active_by_material`.
5. `routers/test.py`: второй роутер и семь обработчиков; регистрация в `create_app()`.
6. Тесты: API, сервис, репозиторий; затем `docs/API.md`.
7. Проверка: `pytest`, `ruff check`, ручной прогон — создать тест → переименовать → перегенерировать →
   опубликовать → попробовать изменить (`409`) → архив → удалить → карточка материала `test: null`.
