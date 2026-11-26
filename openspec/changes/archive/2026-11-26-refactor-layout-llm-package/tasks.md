# Tasks

## 1. Перечисления переезжают в `models/enums.py`

- [x] 1.1 Заменить содержимое `src/testlab/models/enums.py` на определение `UserRole`, `TestStatus`, `QuestionType`, `QuestionSource` (перенести из `src/testlab/domain/enums.py`), файл-реэкспорт удалить; проверить: `grep -r "models.enums" src/` показывает только новые потребители, файл содержит классы, а не импорт
- [x] 1.2 Перевести `models/user.py` и `models/test.py` на `from testlab.models.enums import ...`; проверить: `.\.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider tests/repositories tests/services/test_user_service.py`
- [x] 1.3 Перевести `schemas/user.py`, `schemas/material.py`, `services/user.py`, `services/auth.py`, `services/test.py`, `tests/helpers.py`, `tests/repositories/test_cascade.py`, `tests/services/test_user_service.py` на `testlab.models.enums`; проверить: `.\.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider`

## 2. `LLMResponseError` уезжает в `errors.py`

- [x] 2.1 Перенести `LLMResponseError` в `src/testlab/errors.py` рядом с `LLMError`, сделать подклассом `LLMError` и убрать его строку из `_STATUS_BY_ERROR`; проверить: `.\.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider tests/api/test_errors.py` (ошибка ответа модели по-прежнему даёт `502`)
- [x] 2.2 Удалить `src/testlab/domain/exceptions.py` и перевести на `testlab.errors` тех, кто бросает или импортирует `LLMResponseError`; проверить: `grep -rn "domain.exceptions" src/ tests/` ничего не находит

## 3. Новый пакет `llm/`

- [x] 3.1 Создать `src/testlab/llm/__init__.py`, `src/testlab/llm/prompt.py` (`SYSTEM_PROMPT`, `JSON_EXAMPLE`, `build_user_prompt`) и `src/testlab/llm/generation.py` (перенести `domain/test_generation.py` целиком, импорт `QuestionType` — из `testlab.models.enums`, `LLMResponseError` — из `testlab.errors`); проверить: перенесённый `tests/llm/test_generation.py` (бывший `tests/domain/test_test_generation.py`) зелёный
- [x] 3.2 Создать `src/testlab/llm/client.py` из `infrastructure/llm.py` (транспорт, OAuth, ретрай, импорт промпта из `llm/prompt.py`, DTO из `llm/generation.py`), удалить `src/testlab/infrastructure/llm.py` и пустой `src/testlab/domain/`; проверить: `tests/llm/test_client.py` (бывший `tests/infrastructure/test_llm.py`) зелёный
- [x] 3.3 Перевести `services/test.py`, `dependencies/material.py`, `dependencies/test.py`, `tests/helpers.py` на `testlab.llm.client` и `testlab.llm.generation`; проверить: `.\.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider tests/services tests/api`

## 4. Правила раскладки закреплены тестом

- [x] 4.1 В `tests/test_imports.py` переписать `FORBIDDEN` из `design.md` (решение 7): убрать `domain`, добавить `llm`, `routers` — запрет `testlab.llm`; проверить: `pytest -q -p no:cacheprovider tests/test_imports.py`
- [x] 4.2 Добавить в `tests/test_imports.py` словарь `ALLOWED = {"schemas": {"testlab.models.enums"}}` и учесть его в `is_forbidden`; проверить: тест падает, если вернуть в `schemas/material.py` импорт `testlab.models.test`, и проходит с `testlab.models.enums`
- [x] 4.3 Расширить `test_legacy_modules_removed`: не существуют `testlab/domain`, `testlab/infrastructure/llm.py`, `testlab/models/enums.py` не является реэкспортом; проверить: `pytest -q -p no:cacheprovider tests/test_imports.py`

## 5. Документация раскладки

- [x] 5.1 Обновить `AGENTS.md`: таблица слоёв (строки `domain` нет, есть `llm`), Layout (`llm/`, `models/enums.py`, отсутствие `domain/`), убрать строку про реэкспорт `models.enums`, добавить правило «всё про модель — в `llm/`; новых тематических пакетов не заводить»; проверить: каждый путь, названный в Layout, существует в `src/testlab`, а упомянутого `domain/` нет
- [x] 5.2 Обновить `README.md`: в описании слоёв убрать `domain`, добавить `llm`; проверить: `grep -rn "domain" README.md docs/` не находит устаревших упоминаний слоя

## 6. Интеграционная проверка

- [x] 6.1 Прогнать весь набор и линтер: `.\.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider` и `.\.venv\Scripts\python.exe -m ruff check . --no-cache`; проверить: оба завершаются с кодом 0
- [x] 6.2 Проверить сборку приложения без живого процесса: `.\.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider tests/test_startup.py`; проверить: маршруты регистрируются один раз, приложение импортируется без ссылок на удалённые модули

## Workflow follow-up

- Проверки пройдены: `pytest` — 134 passed, `ruff` — чисто.
- Архивировать изменение после проверки: `openspec archive refactor-layout-llm-package`.
- Убедиться, что `openspec validate --all` чистый и каталог `openspec/changes/refactor-layout-llm-package` перемещён в `archive/`.
