"""Уровень 3. `orders_service/app/users_client.py` + настоящий Users API.

Драйвер вызывает `get_user` напрямую — контроллера Orders API ещё нет.
"""

import pytest
import requests

from lab_kit import DEAD_URL

pytestmark = [pytest.mark.bottomup, pytest.mark.usefixtures("users_client_to_real_users")]


def test_bu4_01_existing_user(orders_svc):
    lookup = orders_svc.users_client.get_user(1)

    assert lookup.user == {"id": 1, "name": "Анна Иванова", "email": "anna@example.com"}
    assert lookup.elapsed_ms > 0


def test_bu4_02_user_created_through_api_is_visible(orders_svc, make_user):
    user = make_user()

    assert orders_svc.users_client.get_user(user["id"]).user == user


def test_bu4_03_missing_user_raises_404(orders_svc):
    with pytest.raises(orders_svc.users_client.UserServiceError) as error:
        orders_svc.users_client.get_user(999)

    assert (error.value.status_code, error.value.detail) == (404, "User 999 not found")


def test_bu4_04_users_api_down_raises_503(orders_svc, monkeypatch):
    monkeypatch.setattr(orders_svc.users_client, "USER_SERVICE_URL", DEAD_URL)

    with pytest.raises(orders_svc.users_client.UserServiceError) as error:
        orders_svc.users_client.get_user(1)

    assert error.value.status_code == 503


def test_bu4_05_request_id_is_forwarded(orders_svc, monkeypatch):
    sent = []
    real_get = requests.get

    def spy(url, **kwargs):
        sent.append(kwargs["headers"].get("X-Request-ID"))
        return real_get(url, **kwargs)

    monkeypatch.setattr(orders_svc.users_client.requests, "get", spy)
    orders_svc.users_client.get_user(1, request_id="bu4-trace")

    assert sent == ["bu4-trace"]


def test_bu4_06_contract_users_response_fits_order_snapshot(orders_svc, users_svc):
    """Поля User в Users API совпадают с UserSnapshot в Orders API — строгость снимка сейчас не мешает."""
    lookup = orders_svc.users_client.get_user(2)

    assert set(lookup.user) == set(orders_svc.models.UserSnapshot.model_fields)
    assert set(users_svc.models.User.model_fields) == set(orders_svc.models.UserSnapshot.model_fields)
    orders_svc.models.UserSnapshot.model_validate(lookup.user)
