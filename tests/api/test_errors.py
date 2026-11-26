"""Маппинг доменных ошибок в HTTP-коды."""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from testlab.dependencies.material import get_file_storage
from testlab.errors import ConflictError, LLMError, PersistenceError, register_exception_handlers
from tests.helpers import create_test, register, upload_material


@pytest.fixture(autouse=True)
def stub_pdf(monkeypatch) -> None:
    monkeypatch.setattr("testlab.services.material.extract_text", lambda content: "текст материала")
    monkeypatch.setattr("testlab.services.test.extract_text", lambda content: "текст материала")


async def test_llm_error_maps_to_502(client, teacher, fake_llm):
    material_id = (await upload_material(client, teacher["headers"])).json()["id"]
    fake_llm.error = LLMError("GigaChat вернул ошибку 500")

    response = await create_test(client, teacher["headers"], material_id)

    assert response.status_code == 502
    assert response.json()["detail"] == "GigaChat вернул ошибку 500"


def test_conflict_error_maps_to_409():
    app = FastAPI()
    register_exception_handlers(app)

    @app.get("/conflict")
    async def conflict() -> None:
        raise ConflictError("Тест для материала уже создан")

    with TestClient(app) as client:
        response = client.get("/conflict")

    assert response.status_code == 409
    assert response.json()["detail"] == "Тест для материала уже создан"


async def test_persistence_error_maps_to_500(app, client, teacher):
    class BrokenStorage:
        async def save(self, content: bytes, filename: str) -> str:
            raise PersistenceError("диск недоступен")

        async def delete(self, path: str) -> None:
            return None

    app.dependency_overrides[get_file_storage] = lambda: BrokenStorage()

    response = await upload_material(client, teacher["headers"])

    assert response.status_code == 500
    assert response.json()["detail"] == "диск недоступен"


async def test_duplicate_registration_maps_to_400(client, teacher):
    response = await client.post(
        "/auth/register",
        json={
            "username": "teacher_one",
            "password": "secret123",
            "full_name": "Дубль",
            "role": "teacher",
        },
    )

    assert response.status_code == 400
    assert "detail" in response.json()


async def test_permission_denied_maps_to_403(client, student):
    response = await client.get("/materials", headers=student["headers"])

    assert response.status_code == 403


async def test_invalid_token_maps_to_401(client):
    response = await client.get("/materials", headers={"Authorization": "Bearer broken"})

    assert response.status_code == 401


async def test_not_found_maps_to_404(client, teacher):
    assert await register(client, "teacher_extra") is not None

    response = await client.get("/materials/2b6e2c1e-0000-4000-8000-000000000000", headers=teacher["headers"])

    assert response.status_code == 404
    assert response.json()["detail"] == "Материал не найден"
