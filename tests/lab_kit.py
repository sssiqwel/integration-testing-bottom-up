"""Общие инструменты для лабораторных «сверху вниз» и «снизу вверх».

Оба сервиса называют свой пакет `app`, поэтому напрямую импортировать их
в один процесс нельзя. `load_service` загружает пакет сервиса и убирает его
из `sys.modules`, чтобы второй сервис загрузился независимо. Модули остаются
живыми, и их можно подменять заглушками через monkeypatch.

`ThreadServer` запускает ASGI-приложение в uvicorn в отдельном потоке:
запросы идут по настоящему HTTP, но подменённые атрибуты модулей видны серверу.
"""

from __future__ import annotations

import importlib
import socket
import sys
import threading
import time
from pathlib import Path
from types import SimpleNamespace

import requests
import uvicorn

ROOT = Path(__file__).resolve().parent.parent
HOST = "127.0.0.1"
TOKEN = "secret-token"
AUTH = {"Authorization": f"Bearer {TOKEN}"}


def load_service(name: str) -> SimpleNamespace:
    """Загрузить `<name>_service/app` и вернуть его модули по коротким именам."""
    service_dir = str(ROOT / f"{name}_service")

    def drop_app_modules() -> dict:
        found = {k: m for k, m in sys.modules.items() if k == "app" or k.startswith("app.")}
        for key in found:
            del sys.modules[key]
        return found

    drop_app_modules()
    sys.path.insert(0, service_dir)
    try:
        importlib.import_module("app.main")
    finally:
        sys.path.remove(service_dir)
        modules = drop_app_modules()
    return SimpleNamespace(**{key.split(".")[-1]: mod for key, mod in modules.items() if "." in key})


def free_port() -> int:
    with socket.socket() as sock:
        sock.bind((HOST, 0))
        return sock.getsockname()[1]


class ThreadServer:
    def __init__(self, app) -> None:
        self.port = free_port()
        self.url = f"http://{HOST}:{self.port}"
        config = uvicorn.Config(app, host=HOST, port=self.port, log_level="critical")
        self._server = uvicorn.Server(config)
        self._thread = threading.Thread(target=self._server.run, daemon=True)

    def start(self) -> "ThreadServer":
        self._thread.start()
        for _ in range(100):
            if self._server.started:
                return self
            time.sleep(0.05)
        raise RuntimeError(f"server on {self.url} did not start")

    def stop(self) -> None:
        self._server.should_exit = True
        self._thread.join(timeout=5)


class ApiClient(requests.Session):
    def __init__(self, base_url: str) -> None:
        super().__init__()
        self.base_url = base_url.rstrip("/")
        self.headers["Accept"] = "application/json"

    def request(self, method, url, *args, **kwargs):
        kwargs.setdefault("timeout", 5)
        return super().request(method, f"{self.base_url}{url}", *args, **kwargs)


DEAD_URL = f"http://{HOST}:9"
