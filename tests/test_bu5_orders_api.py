"""Уровень 4. Верхний модуль — контроллер Orders API.

Все модули под ним уже проверены на уровнях 1–3 и подключены настоящие:
storage, auth, users_client и Users API. Это полная система.
"""

import time

import pytest

from lab_kit import AUTH, DEAD_URL

pytestmark = [pytest.mark.bottomup, pytest.mark.usefixtures("users_client_to_real_users")]


def order(user_id=1, item="Настольная лампа"):
    return {"user_id": user_id, "item": item, "quantity": 1}


def create(orders_api, user_id=1, item="Настольная лампа"):
    response = orders_api.post("/api/v1/orders", json=order(user_id, item), headers=AUTH)
    assert response.status_code == 201, response.text
    return response.json()


def test_bu5_01_end_to_end(orders_api, make_user):
    user = make_user()

    created = orders_api.post("/api/v1/orders", json=order(user["id"]), headers={**AUTH, "X-Request-ID": "bu5"})

    assert created.status_code == 201
    assert created.json()["user"] == user
    assert created.headers["Location"] == "/api/v1/orders/1"
    assert created.headers["X-Request-ID"] == "bu5"
    assert float(created.headers["X-User-Service-Time-Ms"]) > 0
    assert orders_api.get("/api/v1/orders/1").json() == created.json()
    assert [o["id"] for o in orders_api.get("/api/v1/orders").json()] == [1]


@pytest.mark.parametrize(
    ("body", "headers", "status"),
    [
        (order(999), AUTH, 404),
        ({"user_id": 0, "item": " ", "quantity": 0}, AUTH, 422),
        (order(), {}, 401),
    ],
    ids=["missing-user", "invalid-body", "no-token"],
)
def test_bu5_02_errors_do_not_create_orders(orders_api, orders_svc, body, headers, status):
    assert orders_api.post("/api/v1/orders", json=body, headers=headers).status_code == status
    assert orders_svc.storage.storage.list() == []


def test_bu5_03_users_api_down(orders_api, orders_svc, monkeypatch):
    create(orders_api)
    monkeypatch.setattr(orders_svc.users_client, "USER_SERVICE_URL", DEAD_URL)

    assert orders_api.post("/api/v1/orders", json=order(), headers=AUTH).status_code == 503
    assert orders_api.get("/api/v1/orders/1").status_code == 503
    assert orders_api.get("/api/v1/orders").status_code == 503
    assert orders_api.get("/health").status_code == 200
    assert len(orders_svc.storage.storage.list()) == 1


def test_bu5_04_list_time_grows_with_orders(orders_api, orders_svc, monkeypatch):
    """Наблюдение N+1: один и тот же пользователь запрашивается на каждый заказ."""
    for i in range(10):
        create(orders_api, item=f"Товар-{i}")
    calls = []
    real_get_user = orders_svc.main.get_user

    def counting(user_id, request_id=None):
        calls.append(user_id)
        return real_get_user(user_id, request_id=request_id)

    monkeypatch.setattr(orders_svc.main, "get_user", counting)
    started = time.perf_counter()
    listed = orders_api.get("/api/v1/orders")
    took_ms = (time.perf_counter() - started) * 1000

    assert listed.status_code == 200
    assert calls == [1] * 10
    print(f"\nсписок из 10 заказов: {took_ms:.1f} мс, "
          f"X-User-Service-Time-Ms={listed.headers['X-User-Service-Time-Ms']}")


@pytest.mark.defect
@pytest.mark.xfail(strict=True, reason="BU-D2: после рестарта Users один пропавший пользователь роняет GET /orders")
def test_bu5_05_list_after_users_restart(orders_api, make_user, restart_users):
    kept = create(orders_api, 1, "Лампа для Анны")
    create(orders_api, make_user()["id"], "Временный товар")

    restart_users()
    response = orders_api.get("/api/v1/orders")

    assert response.status_code == 200, response.text
    assert kept["id"] in {o["id"] for o in response.json()}


@pytest.mark.defect
@pytest.mark.xfail(strict=True, reason="BU-D3: существующий заказ после рестарта Users отвечает 404")
def test_bu5_06_existing_order_after_users_restart(orders_api, make_user, restart_users):
    created = create(orders_api, make_user()["id"])

    restart_users()
    response = orders_api.get(f"/api/v1/orders/{created['id']}")

    assert response.status_code != 404, response.text


@pytest.mark.defect
@pytest.mark.xfail(strict=True, reason="BU-D4: id пользователя переиспользуется, заказ показывает другого человека")
def test_bu5_07_order_never_shows_another_person(orders_api, make_user, restart_users):
    ivan = make_user("Иван Новиков", "ivan@example.com")
    created = create(orders_api, ivan["id"], "Подарок Ивану")

    restart_users()
    make_user("Мария Сидорова", "maria@example.com")
    shown = orders_api.get(f"/api/v1/orders/{created['id']}")

    assert shown.json().get("user", {}).get("email") != "maria@example.com", shown.text
