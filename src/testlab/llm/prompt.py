"""Промпт для модели: системная инструкция, пример JSON и текст запроса."""

SYSTEM_PROMPT = (
    "Ты методист, который составляет тесты по учебным материалам. "
    "Отвечай только JSON, без markdown-разметки и пояснений."
)

JSON_EXAMPLE = (
    '{"title": "Название теста", "questions": ['
    '{"type": "closed", "text": "Вопрос", "points": 1, '
    '"options": [{"text": "Вариант A", "is_correct": true}, '
    '{"text": "Вариант B", "is_correct": false}, {"text": "Вариант C", "is_correct": false}], '
    '"rubric": null}, '
    '{"type": "open", "text": "Вопрос", "points": 3, "options": null, '
    '"rubric": {"criteria_text": "Что должно быть в ответе", "reference_answer": "Эталонный ответ"}}'
    "]}"
)


def build_user_prompt(text: str, closed_count: int, open_count: int) -> str:
    return "\n".join(
        [
            "Составь тест по тексту ниже.",
            "Верни строго JSON такого вида:",
            JSON_EXAMPLE,
            (
                f"Нужно ровно {closed_count} закрытых вопросов (три варианта, один правильный) "
                f"и {open_count} открытых (с критериями и эталонным ответом)."
            ),
            'Поле "points" — целое число от 1 до 5, по сложности вопроса.',
            "Текст материала:",
            "---",
            text,
            "---",
        ]
    )
