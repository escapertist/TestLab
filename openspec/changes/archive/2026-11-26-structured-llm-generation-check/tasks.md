# Tasks

## 1. Зависимости и схемы ответа

- [x] 1.1 Добавить `langchain-gigachat>=0.5.1` в `dependencies` `pyproject.toml`; проверить `uv sync` и `python -c "from langchain_gigachat import GigaChat"` (на Windows при локе — `UV_CACHE_DIR=.uv-cache`)
- [x] 1.2 Создать `llm/output.py` со схемами `Option`, `Rubric`, `Question`, `Test`, `Verdict`; проверить тестом, что `convert_to_gigachat_tool(Test)` и `convert_to_gigachat_tool(Verdict)` не бросают исключение и не содержат `anyOf`/`oneOf`

## 2. Конфиг и клиенты

- [x] 2.1 Переписать `config/llm_config.py`: `base_url`, `scope`, per-role `generation_model`/`generation_temperature`/`check_model`/`check_temperature`, убрать `model`; проверить `python -m pytest tests/config -q`
- [x] 2.2 Создать `llm/chat.py` с `_chat`, `generation_client`, `check_client`; проверить тестом, что созданный `GigaChat` несёт `model`/`temperature`/`base_url`/`credentials`/`scope` из настроек (создание без сети)
- [x] 2.3 Переписать `llm/client.py` на `TestGenerator` и `AnswerChecker` (Runnable внедряется, `_ensure_counts`, маппинг `ValidationError`/`OutputParserException` → `LLMResponseError`, `GigaChatException` → `LLMError`); проверить `python -m pytest tests/llm/test_client.py -q` на фейковом Runnable
- [x] 2.4 Переписать `llm/prompt.py` (`build_generation_prompt`, `build_check_prompt`, убрать `JSON_EXAMPLE`) и удалить `llm/generation.py`; проверить `python -m pytest tests/llm -q` и отсутствие импортов `parse_generated_test` (`grep`)

## 3. Генерация теста

- [x] 3.1 Расширить `TestCreateRequest` в `schemas/test.py` полями `closed_count`, `open_count`, `options_count` с ограничениями (сумма 1..20, `options_count` 2..10, по умолчанию 4); проверить тестом `422` на пустой состав, сумму больше 20 и `options_count` меньше двух
- [x] 3.2 Перевести `services/test.py` на `generate_test(text, *, closed_count, open_count, options_count)`, `_build_questions` собирает вопросы из единого списка, `generation_params` с запрошенными counts; проверить `python -m pytest tests/services/test_test_service.py -q`
- [x] 3.3 Заменить `_llm_client`/`get_llm_client` на `@lru_cache get_generation_client` в `dependencies/*` и обновить `tests/conftest.py`; проверить `python -m pytest tests/api/test_generation_action.py -q`

## 4. Проверка ответов

- [x] 4.1 Добавить `schemas/answers.py` (`CheckRequest`, `CheckItem`, `CheckResult`) с валидацией списка (непустой, до 20, поля непустые); проверить тестом `422` на пустой список и элемент без поля
- [x] 4.2 Реализовать `services/answers.py` (`CheckService.check_answers`: цикл по элементам, `is_correct` из `AnswerChecker`); проверить `tests/services/test_answers_service.py` (независимость элементов, проброс `LLMError`)
- [x] 4.3 Добавить `routers/answers.py` (`POST /answers/check`, тег `answers`, роль `teacher`) и зарегистрировать в `__main__.py`; проверить `tests/api/test_answers.py` (`200`, `422`, `502`, `401`/`403`) и `tests/test_startup.py`

## 5. Интеграция и документация

- [x] 5.1 Дополнить `tests/test_imports.py` запретом `langchain_core`/`langchain_gigachat` в `services` и `routers`; прогнать `python -m pytest -q -p no:cacheprovider` и `python -m ruff check . --no-cache`
- [x] 5.2 Обновить `AGENTS.md` (состав `llm/`, стек LLM, env-переменные); проверить, что описание слоёв и `llm/` совпадает с кодом
- [x] 5.3 Обновить `docs/API.md`: контракт `POST /materials/{id}/tests` с тремя параметрами и раздел `POST /answers/check`; проверить, что коды и поля совпадают с тестами

## 6. Упрощение модели теста

- [x] 6.1 Убрать `criteria_text` и таблицу `open_question_rubrics`: `reference_answer` стал колонкой `questions`; проверить `python -m pytest -q -p no:cacheprovider`
- [x] 6.2 Убрать `source` и `QuestionSource`; проверить, что упоминаний не осталось (`grep` по `src`, `tests`)
- [x] 6.3 Обновить `docs/API.md`, `docs/er.md`, `docs/sql_scripts.sql`, `AGENTS.md`; проверить, что в описании нет `rubric`/`source`

## Workflow follow-up

- После реализации заархивировать change (`/openspec-archive-change structured-llm-generation-check`), синхронизировав delta-спеки с main-спеками.
