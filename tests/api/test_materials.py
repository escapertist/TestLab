"""Эндпоинты /materials."""

from uuid import uuid4

import pytest

from testlab.config.app_config import settings
from tests.helpers import upload_material


@pytest.fixture(autouse=True)
def stub_pdf(monkeypatch) -> None:
    monkeypatch.setattr("testlab.services.material.extract_text", lambda content: "текст материала")


async def create_material(client, teacher, title: str = "Лекция 1") -> dict:
    response = await upload_material(client, teacher["headers"], title=title)
    assert response.status_code == 201, response.text
    return response.json()


async def test_upload_returns_material_without_test(client, teacher):
    body = await create_material(client, teacher)

    assert body["title"] == "Лекция 1"
    assert body["filename"] == "lecture.pdf"
    assert body["is_uploaded"] is True
    assert body["created_at"].endswith("Z")
    assert "test" not in body


async def test_upload_hides_file_path(client, teacher):
    response = await upload_material(client, teacher["headers"])
    listing = await client.get("/materials", headers=teacher["headers"])
    material_id = response.json()["id"]
    detail = await client.get(f"/materials/{material_id}", headers=teacher["headers"])

    for body in (response.json(), listing.json(), detail.json()):
        assert "file_path" not in str(body)


async def test_upload_rejects_non_pdf(client, teacher):
    response = await upload_material(client, teacher["headers"], filename="notes.txt")

    assert response.status_code == 400
    assert "PDF" in response.json()["detail"]


async def test_upload_rejects_foreign_content_type(client, teacher):
    response = await upload_material(client, teacher["headers"], content_type="text/plain")

    assert response.status_code == 400


async def test_upload_rejects_empty_file(client, teacher):
    response = await upload_material(client, teacher["headers"], content=b"")

    assert response.status_code == 400


async def test_upload_rejects_too_large_file(client, teacher, monkeypatch):
    monkeypatch.setattr(settings, "uploads_max_bytes", 10)

    response = await upload_material(client, teacher["headers"], content=b"x" * 100)

    assert response.status_code == 413


async def test_upload_forbidden_for_student(client, student):
    response = await upload_material(client, student["headers"])

    assert response.status_code == 403


async def test_upload_requires_token(client):
    response = await upload_material(client, {})

    assert response.status_code == 401


async def test_list_returns_own_materials(client, teacher):
    first = await create_material(client, teacher, title="Первая")
    second = await create_material(client, teacher, title="Вторая")

    response = await client.get("/materials", headers=teacher["headers"])

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 2
    assert [item["id"] for item in body["items"]] == [second["id"], first["id"]]


async def test_list_pagination(client, teacher):
    for index in range(3):
        await create_material(client, teacher, title=f"Лекция {index}")

    response = await client.get("/materials?limit=2&offset=1", headers=teacher["headers"])

    body = response.json()
    assert body["total"] == 3
    assert len(body["items"]) == 2


async def test_list_is_isolated(client, teacher, other_teacher):
    await create_material(client, teacher, title="Своя")
    await create_material(client, other_teacher, title="Чужая")

    response = await client.get("/materials", headers=other_teacher["headers"])

    body = response.json()
    assert body["total"] == 1
    assert [item["title"] for item in body["items"]] == ["Чужая"]


@pytest.mark.parametrize("query", ["limit=0", "limit=101", "offset=-1"])
async def test_list_validates_pagination(client, teacher, query):
    response = await client.get(f"/materials?{query}", headers=teacher["headers"])

    assert response.status_code == 422


async def test_detail_returns_material_without_test(client, teacher):
    created = await create_material(client, teacher)

    response = await client.get(f"/materials/{created['id']}", headers=teacher["headers"])

    assert response.status_code == 200
    body = response.json()
    assert body["id"] == created["id"]
    assert body["test"] is None


async def test_detail_foreign_material_is_not_found(client, teacher, other_teacher):
    created = await create_material(client, teacher)

    response = await client.get(f"/materials/{created['id']}", headers=other_teacher["headers"])

    assert response.status_code == 404


async def test_detail_unknown_material(client, teacher):
    response = await client.get(f"/materials/{uuid4()}", headers=teacher["headers"])

    assert response.status_code == 404


async def test_detail_invalid_uuid(client, teacher):
    response = await client.get("/materials/not-a-uuid", headers=teacher["headers"])

    assert response.status_code == 422


async def test_download_file(client, teacher):
    created = await create_material(client, teacher)

    response = await client.get(f"/materials/{created['id']}/file", headers=teacher["headers"])

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert "lecture.pdf" in response.headers["content-disposition"]
    assert response.content.startswith(b"%PDF")


async def test_download_foreign_file(client, teacher, other_teacher):
    created = await create_material(client, teacher)

    response = await client.get(f"/materials/{created['id']}/file", headers=other_teacher["headers"])

    assert response.status_code == 404


async def test_delete_material(client, teacher):
    created = await create_material(client, teacher)

    response = await client.delete(f"/materials/{created['id']}", headers=teacher["headers"])

    assert response.status_code == 204
    assert (await client.get(f"/materials/{created['id']}", headers=teacher["headers"])).status_code == 404
    listing = await client.get("/materials", headers=teacher["headers"])
    assert listing.json()["total"] == 0
    assert (await client.delete(f"/materials/{created['id']}", headers=teacher["headers"])).status_code == 404


async def test_delete_foreign_material(client, teacher, other_teacher):
    created = await create_material(client, teacher)

    response = await client.delete(f"/materials/{created['id']}", headers=other_teacher["headers"])

    assert response.status_code == 404
    assert (await client.get(f"/materials/{created['id']}", headers=teacher["headers"])).status_code == 200


async def test_delete_forbidden_for_student(client, teacher, student):
    created = await create_material(client, teacher)

    response = await client.delete(f"/materials/{created['id']}", headers=student["headers"])

    assert response.status_code == 403
