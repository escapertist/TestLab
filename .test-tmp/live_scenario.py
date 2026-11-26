"""Живой прогон сценария: загрузка → карточка → генерация → карточка → повтор."""

import sys
import uuid

import httpx

sys.path.insert(0, ".")
from tests.helpers import build_pdf_with_text  # noqa: E402

BASE = "http://127.0.0.1:8010"
PASSWORD = "secret123"


def show(step: str, response: httpx.Response) -> httpx.Response:
    print(f"{step}: {response.status_code} {response.text[:200]}")
    return response


def main() -> int:
    client = httpx.Client(base_url=BASE, timeout=120.0)
    username = f"live_{uuid.uuid4().hex[:8]}"
    show(
        "register",
        client.post(
            "/auth/register",
            json={"username": username, "password": PASSWORD, "full_name": "Live", "role": "teacher"},
        ),
    )
    login = show("login", client.post("/auth/login", json={"username": username, "password": PASSWORD}))
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

    upload = show(
        "upload",
        client.post(
            "/materials",
            files={"file": ("lecture.pdf", build_pdf_with_text("Hello TestLab live"), "application/pdf")},
            data={"title": "Живая лекция"},
            headers=headers,
        ),
    )
    assert upload.status_code == 201, upload.text
    assert "test" not in upload.json(), upload.json()
    material_id = upload.json()["id"]

    card = show("card before", client.get(f"/materials/{material_id}", headers=headers))
    assert card.json()["test"] is None
    file_response = show("file", client.get(f"/materials/{material_id}/file", headers=headers))
    assert file_response.status_code == 200 and file_response.content.startswith(b"%PDF")
    no_token = show("no token", client.post(f"/materials/{material_id}/tests"))
    assert no_token.status_code == 401, no_token.text

    generate = show("generate", client.post(f"/materials/{material_id}/tests", headers=headers))
    if generate.status_code == 201:
        body = generate.json()
        print("  questions:", len(body["questions"]), "status:", body["status"], "title:", body["title"])
        card_after = show("card after", client.get(f"/materials/{material_id}", headers=headers))
        assert card_after.json()["test"]["id"] == body["id"]
    else:
        assert generate.status_code == 502, generate.text
        print("  модель недоступна: материал должен остаться без теста")
        card_after = show("card after", client.get(f"/materials/{material_id}", headers=headers))
        assert card_after.json()["test"] is None

    repeat = show("repeat generate", client.post(f"/materials/{material_id}/tests", headers=headers))
    if generate.status_code == 201:
        assert repeat.status_code == 409, repeat.text
    else:
        assert repeat.status_code == 502, repeat.text

    print("live scenario OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
