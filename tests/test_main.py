from fastapi.testclient import TestClient

from config import settings
from main import app
from routers.api import router
from utils.ids import generate_id
from utils.urls import build_api_url, build_client_url


def test_lifespan_creates_tables_when_not_testing(monkeypatch):
    called = []
    monkeypatch.setattr("main.create_all_tables", lambda: called.append(True))
    monkeypatch.setattr(settings, "testing", False)
    with TestClient(app):
        pass
    assert called
    monkeypatch.setattr(settings, "testing", True)


def test_api_router_includes_user_routes():
    assert router.routes


def test_build_urls():
    assert build_client_url("/password/reset/abc") == (
        f"{settings.client_origin.rstrip('/')}/password/reset/abc"
    )
    assert build_client_url("relative") == f"{settings.client_origin.rstrip('/')}/relative"
    api_url = build_api_url("/users/me/activate/token")
    assert settings.api_prefix.rstrip("/") in api_url
    assert api_url.endswith("/users/me/activate/token")
    assert build_api_url("users/")[-6:] == "users/"


def test_generate_id_is_unique():
    first = generate_id()
    second = generate_id()
    assert isinstance(first, int)
    assert first != second
