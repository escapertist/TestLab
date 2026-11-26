"""Живой прогон HTTP-стека с подменённым LLM: 201 → карточка → 409."""

import os
import sys
import uuid

os.environ["DB_URL"] = "sqlite+aiosqlite:///.test-tmp/live-stub.db"
os.environ["UPLOADS_DIR"] = ".test-tmp/live-stub-uploads"

sys.path.insert(0, ".")

from fastapi.testclient import TestClient  # noqa: E402

from testlab.__main__ import create_app  # noqa: E402
from testlab.dependencies.material import get_llm_client  # noqa: E402
from tests.helpers import FakeLLM, build_pdf_with_text  # noqa: E402

PASSWORD = "secret123"


def main() -> int:
    app = create_app()
    app.dependency_overrides[get_llm_client] = lambda: FakeLLM()
    with TestClient(app) as client:
        username = f"stub_{uuid.uuid4().hex[:8]}"
        client.post(
            "/auth/register",
            json={"username": username, "password": PASSWORD, "full_name": "Stub", "role": "teacher"},
        )
        login = client.post("/auth/login", json={"username": username, "password": PASSWORD})
        headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

        upload = client.post(
            "/materials",
            files={"file": ("lecture.pdf", build_pdf_with_text("Hello TestLab"), "application/pdf")},
            data={"title": "Лекция"},
            headers=headers,
        )
        print("upload:", upload.status_code, "test" in upload.json())
        assert upload.status_code == 201 and "test" not in upload.json()
        material_id = upload.json()["id"]

        before = client.get(f"/materials/{material_id}", headers=headers)
        print("card before:", before.status_code, before.json()["test"])
        assert before.json()["test"] is None

        generate = client.post(f"/materials/{material_id}/tests", headers=headers)
        print("generate:", generate.status_code, "questions:", len(generate.json().get("questions", [])))
        assert generate.status_code == 201

        after = client.get(f"/materials/{material_id}", headers=headers)
        print("card after:", after.status_code, after.json()["test"]["id"] == generate.json()["id"])
        assert after.json()["test"]["id"] == generate.json()["id"]

        repeat = client.post(f"/materials/{material_id}/tests", headers=headers)
        print("repeat:", repeat.status_code, repeat.json())
        assert repeat.status_code == 409

    print("live scenario (stub LLM) OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
