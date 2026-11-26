# Design

## Context

См. `proposal.md` — Why. Текущее состояние: [`llm/client.py`](src/testlab/llm/client.py) — ручной
транспорт на `httpx` (OAuth, `self._token`, ретрай на 401, `_post_chat`, `_message_content`),
[`llm/generation.py`](src/testlab/llm/generation.py) — ручной разбор JSON с markdown-обёрткой,
[`llm/prompt.py`](src/testlab/llm/prompt.py) — промпт с примером JSON. Состав теста зашит константами
`CLOSED_QUESTIONS = 5`, `OPEN_QUESTIONS = 2` в [`services/test.py`](src/testlab/services/test.py).
`dependencies/material.py` создаёт `GigaChatClient` на уровне модуля, тесты подменяют его через
`get_llm_client`.

Ограничения: `llm/` — единственное место, где назван провайдер (правило из `AGENTS.md`);
`services`/`routers` не импортируют `langchain*` и `httpx`; `questions.points` имеет `default=1`;
`tests.title` — `NOT NULL`. Модель — `GigaChat-3-Ultra`, доступна только по `scope=GIGACHAT_API_PERS`
и `base_url=https://api.giga.chat/v1`, только для физлиц (freemium).

## Goals / Non-Goals

**Goals:**

- Один способ сборки клиента GigaChat на все роли, без `LLMRole`/`match`/кэша по ролям.
- Структурированный вывод через `with_structured_output` — без ручного JSON-парсинга.
- Состав теста задаётся запросом, а не константами; проверка ответов — отдельным эндпоинтом.

**Non-Goals:**

- Сохранение результатов проверки (`results`/`answers`) — эндпоинт проверки stateless.
- Асинхронная генерация (`202`, очередь), ручная установка `points`, работа с `scope=B2B/CORP`.
- Миграция на GigaChat API v2 (`/v2/chat/completions`) — это альфа `langchain-gigachat 0.5.3a1`.

## Decisions

### 1. `langchain_gigachat` + `with_structured_output(method="function_calling")`

`GigaChat` — LangChain-модель: OAuth и обновление токена внутри SDK, вызов — `await chat.ainvoke([...])`.
`with_structured_output(Schema)` превращает Pydantic-модель в GigaChat-функцию
(`convert_to_gigachat_tool`), принуждает модель вызвать её (`tool_choice` = имя функции) и парсит
аргументы обратно в экземпляр `Schema` через `PydanticToolsParser`. Поэтому из кода исчезают
`OAUTH_URL`, `CHAT_URL`, `self._token`, ретрай на 401 и `parse_generated_test`.

Альтернатива `method="json_schema"` (`response_format`) — на стороне GigaChat beta; берём
`function_calling`, при `422` на схеме меняем метод одной строкой. Отклонено: ручной `httpx` —
не нужен, мы и так добавляем провайдера.

### 2. Клиенты — два экземпляра в `llm/chat.py`, без фабрики

```python
# llm/chat.py
def _chat(model: str, temperature: float) -> GigaChat: ...   # один конструктор
def generation_client() -> Runnable: return _chat(...).with_structured_output(Test)
def check_client() -> Runnable: return _chat(...).with_structured_output(Verdict)
```

Ролей две и отличаются они значениями (`model`, `temperature`), а не логикой — enum и `match` не
нужны. `GigaChat` — Pydantic-модель, конструктор не ходит в сеть (SDK-клиент создаётся лениво),
поэтому сборка безопасна; DI оборачивает вызовы в `@lru_cache`, чтобы тесты могли подменить клиент.

### 3. Схемы ответа в `llm/output.py`

Один список `questions` с дискриминатором `type: QuestionType` и nullable `options`/`reference_answer`.
Nullable допустим: кастомный генератор схемы (`utils/pydantic_generator.py`) убирает `anyOf` для
`X | None` и делает поле необязательным; недопустим только не-nullable `Union` (дискриминированный
`Closed | Open` падает в `gigachat_fix_schema`). `docstring` класса = description функции в промпте,
`title` = имя функции. `points` из схемы убран — дефолт `1.0` из колонки.

### 4. Адаптеры владеют промптом и маппингом ошибок

`llm/client.py` — два класса (`TestGenerator`, `AnswerChecker`), каждый держит `Runnable` (внедряется,
чтобы в тестах подставлять фейк) и строит сообщения. Ошибки: `ValidationError`/`OutputParserException`
→ `LLMResponseError`, `GigaChatException` → `LLMError`, `None` (модель не вызвала функцию) →
`LLMResponseError`. `generation.py` удаляется целиком.

### 5. Конфиг — per-role модель и температура

`LLMConfig`: `credentials`, `scope="GIGACHAT_API_PERS"`, `base_url="https://api.giga.chat/v1"`,
`verify_ssl`, `timeout`, `max_input_chars`; `generation_model="GigaChat-3-Ultra"`,
`generation_temperature=0.2`, `check_model="GigaChat-3-Ultra"`, `check_temperature=0.0`. Поле `model`
и env `GIGACHAT_MODEL` удаляются.

### 6. Лимит 20 — на схеме эндпоинта, а не в схеме GigaChat

`TestCreateRequest` получает `closed_count`, `open_count`, `options_count` с ограничениями
(`options_count` 2..10, сумма 1..20) — это HTTP-валидация Pydantic. Схема GigaChat фиксирует только
форму одного вопроса; количество модель узнаёт из промпта, а соответствие проверяется после парсинга.

### 7. Соответствие составу проверяется в `TestGenerator`

Схема не выражает «ровно N», поэтому после `ainvoke` адаптер сверяет `len(closed) == closed_count`,
`len(open) == open_count`, `len(options) == options_count` и ровно один `is_correct`; расхождение →
`LLMResponseError`. Это ~10 строк, заменяет прежний `_validate_composition`.

### 8. `generation_params` хранит запрошенный состав

Вместо фактического количества по типам пишутся запрошенные `closed_count`, `open_count`,
`options_count` (плюс `model`, `text_chars`, `text_truncated`). Это нужно перегенерации из
`tests-lifecycle-endpoints`: она повторяет те же параметры без повторного запроса клиента.

### 9. Проверка ответов — цикл по элементам

`CheckService.check_answers` валидирует список и последовательно вызывает `AnswerChecker.check_answer`
для каждого элемента, собирая `is_correct`. Выбран последовательный цикл по явному решению;
`asyncio.gather` — зафиксированная альтернатива, если задержка 20 запросов станет проблемой.

### 10. Регистрация роутера и границы импортов

Новый `routers/answers.py` (`POST /answers/check`, тег `answers`) регистрируется в `create_app()`.
`tests/test_imports.py` дополняется запретом `langchain_core`/`langchain_gigachat` в
`services` и `routers`.

### 11. Рубрика и `source` удалены

У открытого вопроса одно поле — `reference_answer` (колонка `questions.reference_answer`); таблица
`open_question_rubrics`, модель `Rubric` и `RubricOut` удалены. `questions.source` и `QuestionSource`
удалены: единственным потребителем был `?force` в перегенерации (change
`tests-lifecycle-endpoints`), а ручного редактирования вопросов пока нет.

## Risks / Trade-offs

- [Ultra доступна только физлицам по `GIGACHAT_API_PERS`] → если креды юрлица, будет `403`; это
  ограничение тарифа, а не кода — проверяется живым запросом при реализации.
- [`function_calling` с вложенной схемой на Ultra может дать `422`] → fallback `method="json_schema"`
  одной строкой; сначала — `function_calling`.
- [Python 3.15: `orjson`/`zstandard`/`xxhash` — бинарные колеса] → `uv sync` обязателен до старта,
  резолв проходит (37 пакетов), но колесо под cp315 надо увидеть фактически.
- [Схема с одним `is_correct: bool` склонна отвечать `true`] → в промпт проверки добавлено требование
  «сравни по смыслу с эталоном; пустой ответ — false».
- [Последовательный цикл = N × время модели] → допустимо для ≤20 ответов; при деградации — `gather`.
- [Ключевые слова схемы (`min_length`/`minItems`) провайдер может игнорировать] → это локальная
  валидация Pydantic, от провайдера она не зависит.
- [`langchain-core` тянет `langsmith`/`requests`/`httpx2`] → рост зависимостей; tracing выключен по
  умолчанию, на работу не влияет.

## Migration Plan

1. `pyproject.toml` + `uv sync`; подтвердить установку на 3.15.
2. `llm/output.py` (схемы), `llm/chat.py` (клиенты), переписать `llm/client.py` и `llm/prompt.py`,
   удалить `llm/generation.py`.
3. `config/llm_config.py`, `schemas/test.py`, `services/test.py`, `dependencies/*`.
4. `routers/answers.py`, регистрация в `__main__.py`.
5. Тесты: переписать `tests/llm/`, обновить `tests/services`, `tests/api`, `tests/test_imports.py`.
6. Согласовать `tests-lifecycle-endpoints` (перегенерация и «7 вопросов»).
7. `docs/API.md`, `AGENTS.md`. Откат — revert коммита; схема БД не меняется.

## Open Questions

- Верхняя граница `options_count` (принято 10) — при необходимости уточняется без изменения спецификаций.
