"""Уровень 1. Users: `models.py` + `storage.py`.

Драйвер — сам тест: он создаёт хранилище и вызывает его методы напрямую,
без HTTP и без контроллера.
"""

import pytest
from pydantic import ValidationError

pytestmark = pytest.mark.bottomup


@pytest.fixture
def store(users_svc):
    return users_svc.storage.UserStorage()


@pytest.fixture
def UserIn(users_svc):
    return users_svc.models.UserIn


def test_bu1_01_seed_users(store):
    assert [(u.id, u.email) for u in store.list()] == [(1, "anna@example.com"), (2, "petr@example.com")]


def test_bu1_02_create_assigns_next_id(store, UserIn):
    user = store.create(UserIn(name="Иван", email="ivan@example.com"))

    assert user.id == 3
    assert store.get(3) == user


def test_bu1_03_model_normalizes_before_storage(store, UserIn):
    user = store.create(UserIn(name="  Иван  ", email="  IVAN@Example.COM "))

    assert (user.name, user.email) == ("Иван", "ivan@example.com")


def test_bu1_04_duplicate_email_differs_only_in_case(store, UserIn, users_svc):
    with pytest.raises(users_svc.storage.DuplicateEmailError):
        store.create(UserIn(name="Другая Анна", email="ANNA@example.com"))
    assert len(store.list()) == 2


@pytest.mark.parametrize(
    "payload",
    [
        {"name": " ", "email": "a@b.ru"},
        {"name": "x" * 101, "email": "a@b.ru"},
        {"name": "Иван", "email": "not-an-email"},
        {"name": "Иван", "email": "a@b.ru", "role": "admin"},
    ],
    ids=["blank-name", "long-name", "bad-email", "extra-field"],
)
def test_bu1_05_invalid_input_is_rejected_by_model(UserIn, payload):
    with pytest.raises(ValidationError):
        UserIn(**payload)


def test_bu1_06_missing_user_is_none(store):
    assert store.get(999) is None


def test_bu1_07_reset_restarts_id_counter(store, UserIn):
    """Наблюдение: после сброса id снова выдаются с 3.

    Для отдельного хранилища это нормально, но Orders API хранит user_id
    у себя — значит, после рестарта Users id может достаться другому
    человеку. Проверяется на уровне 5.
    """
    first = store.create(UserIn(name="Иван", email="ivan@example.com"))
    store.reset()
    second = store.create(UserIn(name="Мария", email="maria@example.com"))

    assert first.id == second.id == 3
    assert store.get(3).name == "Мария"
