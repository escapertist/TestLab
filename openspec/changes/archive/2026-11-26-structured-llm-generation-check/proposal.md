# Proposal

## Why

Клиент GigaChat написан вручную на `httpx`: свой OAuth, хранение токена, ретрай на 401 и ручной
разбор JSON с markdown-обёрткой. Всё это уже умеет `langchain_gigachat` вместе со
`with_structured_output`, а токен SDK получает и обновляет сам — нашему коду он не нужен. Заодно
состав теста сейчас зашит как «ровно 5+2», хотя количество вопросов должно задаваться преподавателем,
а проверки ответов учащегося в сервисе нет вообще.

## What Changes

- Заменить ручной транспорт GigaChat на `langchain_gigachat` с `with_structured_output`: два клиента
  (генерация и проверка), создаваемые в одном файле `llm/chat.py`, без фабрики и без хранения токена.
  **BREAKING** для внутреннего `llm/client.py`.
- Генерация теста становится параметрической: эндпоинт принимает `closed_count`, `open_count`,
  `options_count` (по умолчанию 4), всего вопросов не больше 20. **BREAKING** контракт
  `POST /materials/{material_id}/tests`.
- Убрать `points` из ответа модели — у всех вопросов остаётся дефолт `1.0` из колонки. **BREAKING**
  для ответа API: баллы больше не варьируются и диапазон не проверяется.
- Новый эндпоинт `POST /answers/check`: на вход список `{question_id, question, correct_answer,
  user_answer}`, на выходе тот же список с добавленным `is_correct`; проверка идёт по одному запросу
  в LLM на элемент, цикл в сервисе.
- Удалить ручной разбор ответа модели: `parse_generated_test`, `strip_code_fence`, весь
  transport-код (`OAUTH_URL`, `CHAT_URL`, `self._token`, `_post`, ретрай на 401).
- Убрать `criteria_text` и таблицу `open_question_rubrics`: у открытого вопроса остаётся один
  `reference_answer`, колонка переезжает в `questions`. **BREAKING** для ответа API.
- Убрать `source` и `QuestionSource`: флаг ни на что не влиял, пока нет ручного редактирования
  вопросов. **BREAKING** для ответа API.

## Capabilities

### New Capabilities

- `answers-check`: проверка ответов учащегося — список ответов с вердиктом `is_correct`, один запрос
  в модель на один ответ.

### Modified Capabilities

- `llm-test-generation`: состав теста задаётся запросом (максимум 20 вопросов), структура ответа
  модели задаётся схемой, требования про строгий JSON, markdown-обёртку, баллы и истёкший токен
  удаляются.

## Impact

- `pyproject.toml`: `langchain-gigachat>=0.5.1` (тянет `gigachat 0.2.4`, `langchain-core 1.x`, `httpx2`).
- `src/testlab/config/llm_config.py`: `base_url`, per-role `*_model`/`*_temperature`, убрать `model`.
- `src/testlab/llm/`: новый `chat.py` (два клиента), `output.py` (схемы ответа), переписать `client.py`
  и `prompt.py`, удалить `generation.py`.
- `src/testlab/services/test.py`: сигнатура генерации и сборка вопросов без ветки по `type`.
- `src/testlab/schemas/test.py`: `TestCreateRequest` с тремя новыми полями и лимитом 20.
- `src/testlab/routers/test.py` + новый `routers/answers.py`, регистрация в `__main__.py`.
- In-flight change `tests-lifecycle-endpoints`: перегенерация и её сценарии «7 вопросов / order_index
  1..7» переписываются под параметрический вызов и counts из `generation_params`.
- `docs/API.md`, `docs/er.md`, `docs/sql_scripts.sql`, `AGENTS.md`, `tests/test_imports.py`
  (запрет `langchain*` в `services`/`routers`).
