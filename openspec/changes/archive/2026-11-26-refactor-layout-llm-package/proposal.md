# Proposal

## Why

Директория `domain/` содержит три файла, и ни один из них не является доменом: `enums.py` — словарь значений, которые лежат в колонках БД, `exceptions.py` — одна ошибка, `test_generation.py` — правила разбора ответа языковой модели. Чтобы найти перечисление или ошибку, нужно помнить про отдельный слой, а сам слой не имеет ни одного собственного правила: «`domain/*` может импортировать только stdlib» проверяет пустоту.

Проект будет расти (назначения, результаты, прохождение), и при таком подходе каталоги начнут плодиться на каждую тему. Нужно одно правило размещения: файл лежит в каталоге слоя, а тематический каталог допускается ровно один — `llm/`, потому что код общения с моделью (транспорт, промпт, разбор ответа, DTO) нужен сервисам и адаптерам одновременно и без него не собирается ни одна генерация.

## What Changes

- **`domain/` удаляется**, содержимое расходится по слоям:
  - `enums.py` → `models/enums.py` (все четыре перечисления — типы колонок `SqlEnum`: `users.role`, `tests.status`, `questions.type`, `questions.source`); существующий `models/enums.py` с реэкспортом заменяется определением, второй путь к перечислениям исчезает;
  - `exceptions.py` (`LLMResponseError`) → `errors.py`, рядом с `LLMError` и как его подкласс;
  - `test_generation.py` (`GeneratedTest`/`GeneratedQuestion`/`GeneratedOption`/`GeneratedRubric` + `parse_generated_test`) → новый пакет `llm/`.
- **Новый пакет `llm/`** — единственное тематическое исключение: `client.py` (транспорт GigaChat: OAuth, `/chat/completions`, ретрай на `401`), `prompt.py` (`SYSTEM_PROMPT`, `JSON_EXAMPLE`, `build_user_prompt`), `generation.py` (DTO + правила разбора). `infrastructure/llm.py` удаляется.
- **`infrastructure/` остаётся** с `pdf.py` и `storage.py`: адаптеры к диску и pypdf, к LLM отношения не имеют.
- **`config/llm_config.py` остаётся в `config/`**: настройки всех внешних систем живут в одном месте (`db_config.py` там же, хотя `database.py` — в корне).
- **Правила проверки импортов** в `tests/test_imports.py`: строка `domain` удаляется, добавляется правило для `llm`; `schemas` получает единственное разрешённое исключение — `testlab.models.enums`; отдельный тест фиксирует, что `testlab.domain` больше не существует.
- **Документация**: `AGENTS.md` (таблица слоёв, Layout, правило «всё про модель — в `llm/`; новых тематических пакетов не заводить») и `README.md`.
- **BREAKING (внутреннее)**: ломаются пути импорта `testlab.domain.*` и `testlab.infrastructure.llm` — внешних потребителей пакета нет, все импорты обновляются одним изменением. HTTP-контракт, схема БД и поведение не меняются.

## Capabilities

### New Capabilities

Нет.

### Modified Capabilities

Нет. Это чистый рефакторинг раскладки: ни одно требование `app-startup`, `materials`, `llm-test-generation` не меняется, наблюдаемое поведение остаётся прежним. В `.openspec.yaml` изменения выставлен `skip_specs: true`; придумывать требование о расположении файлов ради валидации не нужно — такие правила живут в `tests/test_imports.py` и `AGENTS.md`.

## Impact

- Код: `src/testlab/domain/` (удаляется), новые `src/testlab/llm/{__init__,client,prompt,generation}.py`, `src/testlab/infrastructure/llm.py` (удаляется), `src/testlab/models/{enums,user,test}.py`, `src/testlab/schemas/{user,material}.py`, `src/testlab/services/{user,auth,test}.py`, `src/testlab/dependencies/{material,test}.py`, `src/testlab/errors.py`.
- Тесты: `tests/domain/` → `tests/llm/`, `tests/infrastructure/test_llm.py` → `tests/llm/test_client.py`, `tests/helpers.py`, `tests/repositories/test_cascade.py`, `tests/services/test_user_service.py`, `tests/test_imports.py`.
- HTTP и данные: без изменений. Миграций нет, схема БД не затрагивается.
- Зависимости: без изменений.
- Документация: `AGENTS.md`, `README.md`.
