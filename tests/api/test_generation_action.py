"""Создание теста по материалу как отдельное действие."""

from pathlib import Path
from uuid import uuid4

import pytest

from testlab.errors import LLMError
from tests.helpers import create_test, upload_material


@pytest.fixture(autouse=True)
def stub_pdf(monkeypatch) -> None:
    monkeypatch.setattr("testlab.services.material.extract_text", lambda content: "текст материала")
    monkeypatch.setattr("testlab.services.test.extract_text", lambda content: "текст материала")


async def upload(client, teacher) -> str:
    response = await upload_material(client, teacher["headers"])
    assert response.status_code == 201, response.text
    return response.json()["id"]


async def test_creates_test_for_material(client, teacher):
    material_id = await upload(client, teacher)
    before = await client.get(f"/materials/{material_id}", headers=teacher["headers"])
    assert before.json()["test"] is None

    response = await create_test(client, teacher["headers"], material_id)

    assert response.status_code == 201, response.text
    body = response.json()
    assert body["status"] == "draft"
    assert len(body["questions"]) == 7
    assert len(body["questions"][0]["options"]) == 2
    assert body["questions"][0]["source"] == "llm"
    assert body["questions"][-1]["rubric"]["criteria_text"] == "Критерии"
    assert body["generation_params"]["closed_count"] == 5
    assert body["generation_params"]["open_count"] == 2

    after = await client.get(f"/materials/{material_id}", headers=teacher["headers"])
    assert after.json()["test"]["id"] == body["id"]


async def test_title_from_body(client, teacher):
    material_id = await upload(client, teacher)

    response = await create_test(client, teacher["headers"], material_id, title="Итоговый тест")

    assert response.status_code == 201
    assert response.json()["title"] == "Итоговый тест"


async def test_second_call_conflicts(client, teacher):
    material_id = await upload(client, teacher)
    first = await create_test(client, teacher["headers"], material_id)

    response = await create_test(client, teacher["headers"], material_id)

    assert response.status_code == 409
    detail = await client.get(f"/materials/{material_id}", headers=teacher["headers"])
    assert detail.json()["test"]["id"] == first.json()["id"]


async def test_foreign_material_is_not_found(client, teacher, other_teacher):
    material_id = await upload(client, teacher)

    response = await create_test(client, other_teacher["headers"], material_id)

    assert response.status_code == 404


async def test_unknown_material_is_not_found(client, teacher):
    response = await create_test(client, teacher["headers"], str(uuid4()))

    assert response.status_code == 404


async def test_llm_error_leaves_material_without_test(client, teacher, fake_llm):
    material_id = await upload(client, teacher)
    fake_llm.error = LLMError("GigaChat недоступен")

    response = await create_test(client, teacher["headers"], material_id)

    assert response.status_code == 502
    assert response.json()["detail"] == "GigaChat недоступен"
    detail = await client.get(f"/materials/{material_id}", headers=teacher["headers"])
    assert detail.json()["test"] is None
    file_response = await client.get(f"/materials/{material_id}/file", headers=teacher["headers"])
    assert file_response.status_code == 200


async def test_missing_file_on_disk(client, teacher, uploads_dir):
    material_id = await upload(client, teacher)
    for path in Path(uploads_dir).iterdir():
        path.unlink()

    response = await create_test(client, teacher["headers"], material_id)

    assert response.status_code == 404


async def test_student_forbidden(client, teacher, student):
    material_id = await upload(client, teacher)

    response = await create_test(client, student["headers"], material_id)

    assert response.status_code == 403


async def test_requires_token(client, teacher):
    material_id = await upload(client, teacher)

    response = await create_test(client, {}, material_id)

    assert response.status_code == 401
