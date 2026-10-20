import pytest

from lab_kit import AUTH, DEAD_URL, ApiClient, ThreadServer, load_service


@pytest.fixture(scope="session")
def users_svc():
    return load_service("users")


@pytest.fixture(scope="session")
def orders_svc():
    return load_service("orders")


@pytest.fixture(scope="session")
def users_server(users_svc):
    server = ThreadServer(users_svc.main.app).start()
    yield server
    server.stop()


@pytest.fixture(scope="session")
def orders_server(orders_svc):
    server = ThreadServer(orders_svc.main.app).start()
    yield server
    server.stop()


@pytest.fixture
def users_api(users_server):
    with ApiClient(users_server.url) as client:
        yield client


@pytest.fixture
def orders_api(orders_server):
    with ApiClient(orders_server.url) as client:
        yield client


@pytest.fixture(autouse=True)
def clean_state(users_svc, orders_svc, monkeypatch):
    """Каждый тест начинает с чистых хранилищ и без подмен.

    Адрес Users API по умолчанию указывает в никуда, чтобы тест случайно
    не обратился к сервису, запущенному на машине вручную.
    """
    users_svc.storage.storage.reset()
    orders_svc.storage.storage.reset()
    monkeypatch.setattr(orders_svc.users_client, "USER_SERVICE_URL", DEAD_URL)


@pytest.fixture
def users_client_to_real_users(orders_svc, users_server, monkeypatch):
    """users_client Orders API смотрит на настоящий Users API."""
    monkeypatch.setattr(orders_svc.users_client, "USER_SERVICE_URL", users_server.url)
    return orders_svc.users_client


@pytest.fixture
def restart_users(users_svc):
    """Users API хранит данные в памяти: рестарт процесса = сброс хранилища."""
    return users_svc.storage.storage.reset


@pytest.fixture
def make_user(users_api):
    def make(name="Иван Новиков", email="ivan@example.com"):
        response = users_api.post("/api/v1/users", json={"name": name, "email": email}, headers=AUTH)
        assert response.status_code == 201, response.text
        return response.json()

    return make
