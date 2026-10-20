"""Уровень 2. Users API целиком: контроллер + auth над проверенными models/storage.

Драйвер — HTTP-клиент `requests`, который заменяет ещё не подключённый
Orders API.
"""

import pytest

from lab_kit import AUTH

pytestmark = pytest.mark.bottomup

IVAN = {"name": "Иван Новиков", "email": "ivan@example.com"}


def test_bu3_01_health_and_list(users_api):
    assert users_api.get("/health").json() == {"status": "ok"}
    assert [u["id"] for u in users_api.get("/api/v1/users").json()] == [1, 2]


def test_bu3_02_create_returns_location_and_is_readable(users_api):
    created = users_api.post("/api/v1/users", json=IVAN, headers=AUTH)

    assert created.status_code == 201
    assert created.headers["Location"] == "/api/v1/users/3"
    assert users_api.get("/api/v1/users/3").json() == {"id": 3, **IVAN}


def test_bu3_03_duplicate_email_is_409(users_api):
    response = users_api.post("/api/v1/users", json={"name": "Анна", "email": "Anna@Example.com"}, headers=AUTH)

    assert response.status_code == 409
    assert response.json() == {"detail": "User with email anna@example.com already exists"}


def test_bu3_04_errors_of_get(users_api):
    assert users_api.get("/api/v1/users/999").status_code == 404
    assert users_api.get("/api/v1/users/abc").status_code == 422


def test_bu3_05_invalid_body_is_422(users_api):
    response = users_api.post("/api/v1/users", json={"name": " ", "email": "x"}, headers=AUTH)

    assert response.status_code == 422


@pytest.mark.parametrize(
    ("headers", "detail"),
    [({}, "Missing Authorization header"), ({"Authorization": "Bearer wrong"}, "Invalid token")],
    ids=["no-token", "wrong-token"],
)
def test_bu3_06_auth(users_api, users_svc, headers, detail):
    response = users_api.post("/api/v1/users", json=IVAN, headers=headers)

    assert response.status_code == 401
    assert response.json() == {"detail": detail}
    assert len(users_svc.storage.storage.list()) == 2


def test_bu3_07_request_id_echo_and_generation(users_api):
    echoed = users_api.get("/health", headers={"X-Request-ID": "bu3-trace"})
    generated = users_api.get("/health")

    assert echoed.headers["X-Request-ID"] == "bu3-trace"
    assert len(generated.headers["X-Request-ID"]) == 36


@pytest.mark.defect
@pytest.mark.xfail(strict=True, reason="BU-D1: при схеме Basic ответ «Missing Authorization header», хотя заголовок есть")
def test_bu3_08_wrong_scheme_has_clear_message(users_api):
    response = users_api.post("/api/v1/users", json=IVAN, headers={"Authorization": "Basic c2VjcmV0"})

    assert response.status_code == 401
    assert response.json()["detail"] != "Missing Authorization header"
