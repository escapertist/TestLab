"""Проверка ответов: контракт, роли и ошибки модели."""

from uuid import uuid4

from testlab.errors import LLMError


def payload() -> dict:
    return {
        "answers": [
            {
                "question_id": str(uuid4()),
                "question": "Столица Франции?",
                "correct_answer": "Париж",
                "user_answer": "Париж",
            },
            {
                "question_id": str(uuid4()),
                "question": "Столица Италии?",
                "correct_answer": "Рим",
                "user_answer": "",
            },
        ]
    }


async def test_checks_list(client, teacher, fake_checker):
    body = payload()

    response = await client.post("/answers/check", json=body, headers=teacher["headers"])

    assert response.status_code == 200, response.text
    answers = response.json()["answers"]
    assert [item["question_id"] for item in answers] == [item["question_id"] for item in body["answers"]]
    assert [item["is_correct"] for item in answers] == [True, True]
    assert fake_checker.calls == [
        ("Столица Франции?", "Париж", "Париж"),
        ("Столица Италии?", "Рим", ""),
    ]


async def test_empty_list_is_rejected(client, teacher):
    response = await client.post("/answers/check", json={"answers": []}, headers=teacher["headers"])

    assert response.status_code == 422


async def test_missing_field_is_rejected(client, teacher):
    body = {"answers": [{"question_id": str(uuid4()), "question": "Только вопрос"}]}

    response = await client.post("/answers/check", json=body, headers=teacher["headers"])

    assert response.status_code == 422


async def test_student_forbidden(client, student):
    response = await client.post("/answers/check", json=payload(), headers=student["headers"])

    assert response.status_code == 403


async def test_requires_token(client):
    response = await client.post("/answers/check", json=payload())

    assert response.status_code == 401


async def test_model_error(client, teacher, fake_checker):
    fake_checker.error = LLMError("GigaChat недоступен")

    response = await client.post("/answers/check", json=payload(), headers=teacher["headers"])

    assert response.status_code == 502
    assert response.json()["detail"] == "GigaChat недоступен"
