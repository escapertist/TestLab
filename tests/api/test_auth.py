"""Эндпоинты /auth."""

from tests.helpers import PASSWORD, register


async def register_payload(username: str, role: str = "teacher") -> dict:
    return {
        "username": username,
        "password": PASSWORD,
        "full_name": f"Пользователь {username}",
        "role": role,
    }


async def test_register_returns_profile(client):
    response = await client.post("/auth/register", json=await register_payload("alice"))

    assert response.status_code == 201
    body = response.json()
    assert body["username"] == "alice"
    assert body["role"] == "teacher"
    assert body["created_at"].endswith("Z")


async def test_register_rejects_duplicate(client, teacher):
    response = await client.post("/auth/register", json=await register_payload("teacher_one"))

    assert response.status_code == 400
    assert "уже существует" in response.json()["detail"]


async def test_register_validates_payload(client):
    response = await client.post(
        "/auth/register",
        json={"username": "ab", "password": "short", "full_name": "И", "role": "teacher"},
    )

    assert response.status_code == 422


async def test_login_returns_token(client, teacher):
    response = await client.post(
        "/auth/login",
        json={"username": "teacher_one", "password": PASSWORD},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["access_token"] == teacher["id"]
    assert body["token_type"] == "bearer"


async def test_login_rejects_wrong_password(client, teacher):
    response = await client.post(
        "/auth/login",
        json={"username": "teacher_one", "password": "wrong-password"},
    )

    assert response.status_code == 401


async def test_me_returns_current_user(client, teacher):
    response = await client.get("/auth/me", headers=teacher["headers"])

    assert response.status_code == 200
    assert response.json()["id"] == teacher["id"]


async def test_me_requires_token(client):
    assert (await client.get("/auth/me")).status_code == 401


async def test_me_rejects_unknown_token(client):
    response = await client.get(
        "/auth/me",
        headers={"Authorization": "Bearer 0a5a0b6a-1111-4222-8333-444455556666"},
    )

    assert response.status_code == 401


async def test_created_at_has_same_format_everywhere(client):
    await client.post("/auth/register", json=await register_payload("bob"))
    login = await client.post("/auth/login", json={"username": "bob", "password": PASSWORD})
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
    me = await client.get("/auth/me", headers=headers)
    again = await client.post("/auth/login", json={"username": "bob", "password": PASSWORD})

    timestamps = {
        login.json()["created_at"],
        me.json()["created_at"],
        again.json()["created_at"],
    }
    assert len(timestamps) == 1
    assert timestamps.pop().endswith("Z")


async def test_registered_user_can_use_materials(client, teacher):
    assert await register(client, "teacher_three", role="teacher") is not None
    assert teacher["headers"]["Authorization"].startswith("Bearer ")
