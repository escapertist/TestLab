# Design

## Context

См. `proposal.md` — Why. Текущее состояние и факты, на которых держится решение:

- `src/testlab/domain/` — три файла: `enums.py` (14 строк), `exceptions.py` (3), `test_generation.py` (144).
- `src/testlab/infrastructure/llm.py` (131 строка) смешивает три вещи: константы промпта и `build_user_prompt`, OAuth + вызов `/chat/completions`, и единственный вызов `parse_generated_test`.
- `src/testlab/models/enums.py` — реэкспорт из домена, который никто не импортирует: `models/user.py` и `models/test.py` берут перечисления напрямую из `testlab.domain.enums`. Второй путь к тем же именам существует только «на совместимость».
- Перечисления используются в `models` (2 файла, `SqlEnum`-колонки), `schemas` (2), `services` (3), парсере и тестах.
- Измерено в venv: `import testlab.schemas.material` не тянет SQLAlchemy, `import testlab.models.enums` тянет — потому что импорт подмодуля выполняет `models/__init__.py`, а тот импортирует все модели.
- `tests/test_imports.py` содержит 5 строк `FORBIDDEN` (`routers`, `services`, `repositories`, `domain`, `schemas`) и три теста; правила проверяются статическим разбором AST.
- Всё дерево `domain/`, `infrastructure/`, `errors.py`, `tests/` ещё не закоммичено (`git status` — untracked), поэтому перемещение стоит только правок импортов.

Ограничения: миграций нет и схема БД не меняется; сервис один процесс, отдельной сборки контрактов (SDK, отдельный пакет) нет; Python 3.15, проверки — `pytest` и `ruff check`.

## Goals / Non-Goals

**Goals:**

- Одно правило размещения файла: каталог = слой; тематический каталог ровно один — `llm/`.
- Ноль изменений наблюдаемого поведения: те же HTTP-коды, те же ответы, та же схема БД.
- Правила раскладки проверяются тестом, а не только описаны в `AGENTS.md`.

**Non-Goals:**

- Переименование `infrastructure/` в `adapters/` или `external/`: смысл не меняется, а правок в доке и импортах прибавится.
- Перенос `config/llm_config.py` в `llm/`: настройки остаются в `config/` вместе с `db_config.py` (прецедент: `database.py` в корне, его настройки — в `config/`).
- Расширение `llm/` до вида `llm_services` из другого проекта (`embeddings`, `factory`, `token_usage_callback`): в этом проекте у модели одна задача — генерация теста по тексту.
- Слияние `pdf.py` и `storage.py` в один модуль или каталог `files/`: это второй тематический каталог, от которого мы отказались.

## Decisions

### 1. Итоговая структура

```text
src/testlab/
  __main__.py
  database.py
  errors.py          + LLMResponseError(LLMError)
  security.py
  init_db.py
  config/            base_config, db_config, llm_config, app_config
  dependencies/      uow, user, auth, material, test
  infrastructure/    pdf.py, storage.py
  llm/               client.py, prompt.py, generation.py      <- новый пакет
  models/            user, material, test, enums.py (определение)
  repositories/      uow, user, material, test
  routers/           user, material, test
  schemas/           common, user, material, test
  services/          user, auth, material, test
```

Директорий девять — столько же, сколько до изменения: `domain` уходит, `llm` приходит, `infrastructure` остаётся.

### 2. Перечисления — в `models/enums.py`

Все четыре (`UserRole`, `TestStatus`, `QuestionType`, `QuestionSource`) — значения колонок `SqlEnum`: `users.role`, `tests.status`, `questions.type`, `questions.source`. Дом «модели» точен: перечисление описывает, что хранится в БД, а `schemas` и `services` — потребители.

`schemas → models.enums` — зависимость вниз по графу (`routers → schemas → services → repositories → models`), а не инверсия. Запрет `schemas ✗ models` в `test_imports.py` вводился ради двух вещей: не связывать HTTP-контракт с ORM-слоем и не тянуть SQLAlchemy в `schemas`. Первое ослаблено сознательно, второе принимается ценой (см. Risks).

Альтернативы: `testlab/enums.py` в корне (ноль исключений в правилах, но лишний корневой модуль и перечисления «нигде»); оставить `domain/enums.py` (слой без правил); `schemas/enums.py` (ORM зависел бы от DTO-модуля — настоящая инверсия).

### 3. `llm/` — единственное тематическое исключение

Пакет собирает всё, что зависит от модели: транспорт (`client.py`), промпт (`prompt.py`), разбор ответа и DTO (`generation.py`). Причина существования: эти три части меняются вместе и нужны сразу двум слоям — `services/test.py` (DTO и клиент) и `infrastructure`/`services` (ничего из этого не импортирует моделей БД, кроме `QuestionType`, который теперь в `models`).

Что это даёт по сравнению с предыдущим вариантом: парсер не уезжает в `services/` и `GigaChatClient.generate_test` продолжает возвращать `GeneratedTest` — контракт клиента и `tests/llm/test_client.py` не переписываются.

Правило на будущее фиксируется в `AGENTS.md`: «всё про модель — в `llm/`; новых тематических пакетов не заводить, новый код идёт в каталог слоя».

### 4. `client.py` и `prompt.py` — разделение по ответственности

Промпт — это данные и одна чистая функция: `SYSTEM_PROMPT`, `JSON_EXAMPLE`, `build_user_prompt(text, closed_count, open_count)`. Её можно тестировать без `httpx` и без фикстур транспорта. Клиент — OAuth, ретрай, разбор HTTP-ответа. Разделение не меняет ни одного вызова: `generate_test` остаётся в `GigaChatClient`.

### 5. `LLMResponseError` становится подклассом `LLMError`

Сейчас это самостоятельный `Exception` с отдельной строкой в `_STATUS_BY_ERROR`. Как подкласс `LLMError` он попадает в `502` через поиск обработчика по MRO (Starlette перебирает `type(exc).__mro__`), а лишняя строка маппинга удаляется. Поведение HTTP не меняется; сохраняется тестом `tests/api/test_errors.py`.

### 6. `infrastructure/` остаётся

`pdf.py` (pypdf) и `storage.py` (диск) — адаптеры внешнего мира, к модели отношения не имеют. Директория на два файла выглядит мелко, но именно она — адрес правила «сеть, диск и PDF живут здесь, сервисы их не реализуют»: `services` запрещено импортировать `httpx`, а бросок `PersistenceError`/`NotFoundError` в хранилище — часть этого контракта. Слияние в `files.py` смешало бы два разных набора ошибок (`MaterialValidationError` у PDF, `PersistenceError`/`NotFoundError` у хранилища), а `files/` добавил бы второй тематический каталог.

### 7. Правила в `tests/test_imports.py`

Строка `domain` удаляется, добавляется `llm`, у `schemas` появляется явное исключение:

```python
FORBIDDEN = {
    "routers": {"testlab.models", "testlab.repositories", "testlab.database",
                "testlab.infrastructure", "testlab.llm"},
    "services": {"fastapi", "starlette", "sqlalchemy", "httpx"},
    "repositories": {"testlab.services", "testlab.infrastructure", "testlab.llm"},
    "llm": {"testlab.services", "testlab.repositories", "testlab.routers",
            "testlab.database", "fastapi", "sqlalchemy"},
    "schemas": {"testlab.models", "testlab.services", "testlab.repositories",
                "testlab.infrastructure", "testlab.database", "testlab.llm"},
    "infrastructure": {"testlab.models", "testlab.services", "testlab.repositories"},
}
ALLOWED = {"schemas": {"testlab.models.enums"}}
```

`is_forbidden` сначала проверяет `ALLOWED[layer]`, иначе исключение нельзя выразить точно. Тест `test_legacy_modules_removed` расширяется: не существует `testlab/domain`, `testlab/infrastructure/llm.py`, а перечисления импортируются из `testlab.models.enums`.

`routers` запрещён `testlab.llm` явно: роутер, зовущий модель напрямую, обошёл бы сервис.

### 8. Тесты переезжают вместе с кодом

```text
tests/domain/test_test_generation.py   -> tests/llm/test_generation.py
tests/infrastructure/test_llm.py       -> tests/llm/test_client.py
```

`tests/helpers.py` берёт `parse_generated_test` из `testlab.llm.generation`. Заглушки `monkeypatch.setattr("testlab.services.material.extract_text", ...)` и `testlab.services.test.extract_text` не меняются — они патчат имя в модуле-потребителе, а не путь адаптера.

## Risks / Trade-offs

- [`schemas` транзитивно тянет SQLAlchemy при импорте `models.enums`] → цена осознанная: сервис один процесс, отдельного потребителя контрактов нет. Выражена одним явным исключением в `ALLOWED`; если станет мешать, возврат перечислений в корневой `testlab/enums.py` — отдельное маленькое изменение.
- [`LLMResponseError` меняет базу на `LLMError` — где-то могли ловить именно его] → в коде такой обработки нет, маппинг идёт по MRO; проверяется `tests/api/test_errors.py` (`502` на ответе модели).
- [Внутренние импорты ломаются у внешних потребителей пакета] → потребителей нет, пакет ставится только для этого сервиса; дерево не закоммичено, откат — `git checkout`/удаление каталогов.
- [Правила импорта становятся слабее из-за `ALLOWED`] → исключение одно, записано в `AGENTS.md` явно, покрыто тестом на отсутствие `testlab.domain`.
- [Один change двигает 20+ файлов, легко получить половину состояния] → порядок в `tasks.md` такой, что `pytest` зелёный после каждого шага; проверка `ruff` в конце.

## Migration Plan

1. `models/enums.py` — определение перечислений; поправить импорты в `models/user.py`, `models/test.py`.
2. `errors.py` — перенести `LLMResponseError` и сделать его подклассом `LLMError`, убрать его из `_STATUS_BY_ERROR`; удалить `domain/exceptions.py`.
3. Создать `llm/prompt.py`, `llm/client.py`, `llm/generation.py`; удалить `infrastructure/llm.py` и `testlab/domain/`.
4. Обновить импорты в `schemas/`, `services/`, `dependencies/`, тестах и `tests/helpers.py`; перенести тесты в `tests/llm/`.
5. Переписать правила `tests/test_imports.py`, расширить `test_legacy_modules_removed`.
6. Обновить `AGENTS.md` (таблица слоёв, Layout, правило про `llm/`) и `README.md`.
7. Проверка: `.\.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider`, `.\.venv\Scripts\python.exe -m ruff check . --no-cache`, запуск приложения проверяется тестом `tests/test_startup.py` (живой reload-процесс требует именованных каналов, запрещённых песочницей).

Откат — revert коммита; данных и схемы изменение не касается.
