"""Уровень 1. Orders: `models.py` + `storage.py`. Драйвер — сам тест."""

import pytest
from pydantic import ValidationError

pytestmark = pytest.mark.bottomup

ANNA = {"id": 1, "name": "Анна Иванова", "email": "anna@example.com"}


@pytest.fixture
def store(orders_svc):
    return orders_svc.storage.OrderStorage()


@pytest.fixture
def OrderIn(orders_svc):
    return orders_svc.models.OrderIn


def test_bu2_01_empty_on_start(store):
    assert store.list() == []


def test_bu2_02_create_get_list(store, OrderIn):
    first = store.create(OrderIn(user_id=1, item="Лампа", quantity=2))
    second = store.create(OrderIn(user_id=2, item="Кружка", quantity=1))

    assert (first.id, second.id) == (1, 2)
    assert store.get(2).item == "Кружка"
    assert [o.id for o in store.list()] == [1, 2]


def test_bu2_03_item_is_trimmed(OrderIn):
    assert OrderIn(user_id=1, item="  Лампа ", quantity=1).item == "Лампа"


@pytest.mark.parametrize(
    "payload",
    [
        {"user_id": 0, "item": "Лампа", "quantity": 1},
        {"user_id": 1, "item": "   ", "quantity": 1},
        {"user_id": 1, "item": "Лампа", "quantity": 0},
        {"user_id": 1, "item": "Лампа", "quantity": 1001},
        {"user_id": 1, "item": "Лампа", "quantity": 1, "price": 10},
    ],
    ids=["user-id-0", "blank-item", "zero-qty", "too-many", "extra-field"],
)
def test_bu2_04_invalid_order_rejected(OrderIn, payload):
    with pytest.raises(ValidationError):
        OrderIn(**payload)


def test_bu2_05_storage_does_not_know_about_users(store, OrderIn):
    """Хранилище заказов принимает любой user_id: проверка пользователя — забота уровня выше."""
    order = store.create(OrderIn(user_id=424242, item="Лампа", quantity=1))

    assert order.user_id == 424242


def test_bu2_06_order_model_builds_from_stored_order_and_user(store, OrderIn, orders_svc):
    stored = store.create(OrderIn(user_id=1, item="Лампа", quantity=2))

    order = orders_svc.models.Order(
        id=stored.id, user_id=stored.user_id, item=stored.item, quantity=stored.quantity, user=ANNA
    )

    assert order.user.email == "anna@example.com"


def test_bu2_07_user_snapshot_is_strict(orders_svc):
    """Наблюдение: снимок пользователя не принимает лишних полей.

    Пока неясно, дефект ли это: всё зависит от того, что реально отдаёт
    Users API. Проверяется на уровне 4.
    """
    with pytest.raises(ValidationError):
        orders_svc.models.UserSnapshot(**ANNA, phone="+7 900 000-00-00")
