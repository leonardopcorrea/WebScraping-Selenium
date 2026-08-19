"""Authentication modes with httpx.MockTransport (no live network)."""

from pathlib import Path

import httpx
import pytest

from scraper.auth import authenticate
from scraper.config import Settings
from scraper.exceptions import AuthError

FIXTURES = Path(__file__).parent / "fixtures"
LOGIN_URL = "https://example.test/login"
BASE_URL = "https://example.test/app/"


@pytest.fixture
def login_html() -> str:
    return (FIXTURES / "login_page.html").read_text(encoding="utf-8")


@pytest.fixture
def login_success_html() -> str:
    return (FIXTURES / "login_success.html").read_text(encoding="utf-8")


@pytest.fixture
def login_failed_html() -> str:
    return (FIXTURES / "login_failed.html").read_text(encoding="utf-8")


def test_cookie_mode_sets_headers(login_success_html: str) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text=login_success_html)

    settings = Settings(
        _env_file=None,
        auth_mode="cookie",
        cookie_header="session=deadbeef",
        auth_bearer="tok123",
        base_url=BASE_URL,
    )
    transport = httpx.MockTransport(handler)
    with httpx.Client(transport=transport) as client:
        authenticate(client, settings)
        assert client.headers["Cookie"] == "session=deadbeef"
        assert client.headers["Authorization"] == "Bearer tok123"


def test_cookie_mode_requires_cookie_or_bearer() -> None:
    with pytest.raises(ValueError, match="COOKIE_HEADER or AUTH_BEARER"):
        Settings(_env_file=None, auth_mode="cookie")


def test_form_login_posts_and_verifies(
    login_html: str,
    login_success_html: str,
) -> None:
    post_seen = {"value": False}

    def handler(request: httpx.Request) -> httpx.Response:
        if request.method == "GET" and request.url.path == "/login":
            return httpx.Response(200, text=login_html)
        if request.method == "POST" and request.url.path == "/login":
            body = request.content.decode()
            assert "username=good" in body
            assert "password=secret" in body
            assert "csrf_token=abc123" in body
            post_seen["value"] = True
            return httpx.Response(200, text=login_success_html, request=request)
        if request.method == "GET" and request.url.path == "/app/":
            return httpx.Response(200, text=login_success_html)
        return httpx.Response(404)

    settings = Settings(
        _env_file=None,
        auth_mode="form",
        login_url=LOGIN_URL,
        username="good",
        password="secret",
        base_url=BASE_URL,
    )
    transport = httpx.MockTransport(handler)
    with httpx.Client(transport=transport, follow_redirects=True) as client:
        authenticate(client, settings)

    assert post_seen["value"] is True


def test_form_login_fails_when_form_still_visible(
    login_html: str,
    login_failed_html: str,
) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.method == "GET" and request.url.path == "/login":
            return httpx.Response(200, text=login_html)
        if request.method == "POST" and request.url.path == "/login":
            return httpx.Response(200, text=login_failed_html, request=request)
        return httpx.Response(404)

    settings = Settings(
        _env_file=None,
        auth_mode="form",
        login_url=LOGIN_URL,
        username="bad",
        password="wrong",
        base_url=BASE_URL,
    )
    transport = httpx.MockTransport(handler)
    with httpx.Client(transport=transport) as client:
        with pytest.raises(AuthError, match="login form still present"):
            authenticate(client, settings)


def test_verify_session_fails_on_401(login_success_html: str) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/app/":
            return httpx.Response(401, text="unauthorized")
        return httpx.Response(200, text=login_success_html)

    settings = Settings(
        _env_file=None,
        auth_mode="cookie",
        cookie_header="session=abc",
        base_url=BASE_URL,
    )
    transport = httpx.MockTransport(handler)
    with httpx.Client(transport=transport, headers={"Cookie": "session=abc"}) as client:
        with pytest.raises(AuthError, match="session probe returned HTTP 401"):
            authenticate(client, settings)


def test_verify_session_fails_when_login_page_returned(
    login_html: str,
) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text=login_html, request=request)

    settings = Settings(
        _env_file=None,
        auth_mode="cookie",
        cookie_header="session=expired",
        login_url=LOGIN_URL,
        base_url=LOGIN_URL,
    )
    transport = httpx.MockTransport(handler)
    with httpx.Client(transport=transport) as client:
        with pytest.raises(AuthError, match="session probe still shows login page"):
            authenticate(client, settings)


def test_form_mode_requires_login_url_and_credentials(monkeypatch) -> None:
    monkeypatch.delenv("LOGIN_URL", raising=False)
    monkeypatch.delenv("USERNAME", raising=False)
    monkeypatch.delenv("PASSWORD", raising=False)

    with pytest.raises(ValueError, match="LOGIN_URL"):
        Settings(_env_file=None, auth_mode="form", username="u", password="p")
    with pytest.raises(ValueError, match="USERNAME"):
        Settings(_env_file=None, auth_mode="form", login_url=LOGIN_URL, password="p")
    with pytest.raises(ValueError, match="PASSWORD"):
        Settings(_env_file=None, auth_mode="form", login_url=LOGIN_URL, username="u")


def test_browser_mode_missing_playwright(monkeypatch) -> None:
    import builtins

    real_import = builtins.__import__

    def fake_import(name, *args, **kwargs):
        if name == "playwright.sync_api":
            raise ImportError("no playwright")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)

    settings = Settings(
        _env_file=None,
        auth_mode="browser",
        login_url=LOGIN_URL,
        username="u",
        password="p",
        base_url=BASE_URL,
    )
    client = httpx.Client()
    with pytest.raises(AuthError, match="requires Playwright"):
        authenticate(client, settings)
