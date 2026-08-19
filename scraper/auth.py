"""Optional authentication before paginated scraping."""

from __future__ import annotations

import httpx
from selectolax.parser import HTMLParser

from scraper.config import Settings
from scraper.exceptions import AuthError
from scraper.logging_setup import logger_for

_LOG = logger_for()


def authenticate(client: httpx.Client, settings: Settings) -> None:
    """Establish a session on the shared httpx client when AUTH_MODE is enabled."""
    if settings.auth_mode == "off":
        return

    log = _LOG
    log.info("authenticating", extra={"auth_mode": settings.auth_mode})

    if settings.auth_mode == "cookie":
        _apply_cookie_auth(client, settings)
    elif settings.auth_mode == "form":
        _form_login(client, settings)
    elif settings.auth_mode == "browser":
        _browser_login(client, settings)
    else:
        raise AuthError(f"unsupported AUTH_MODE: {settings.auth_mode}")

    _verify_session(client, settings)


def _apply_cookie_auth(client: httpx.Client, settings: Settings) -> None:
    if settings.cookie_header:
        client.headers["Cookie"] = settings.cookie_header
    if settings.auth_bearer:
        client.headers["Authorization"] = f"Bearer {settings.auth_bearer}"


def _form_login(client: httpx.Client, settings: Settings) -> None:
    login_url = str(settings.login_url)
    response = client.get(login_url)
    if response.status_code in {401, 403}:
        raise AuthError(
            f"login page returned HTTP {response.status_code}",
            login_url=login_url,
        )
    if response.status_code >= 400:
        raise AuthError(
            f"could not load login page: HTTP {response.status_code}",
            login_url=login_url,
        )

    payload = _extract_form_payload(response.text, settings)
    username_field = _username_field_name(settings, response.text)
    password_field = _password_field_name(settings, response.text)
    payload[username_field] = settings.username or ""
    payload[password_field] = settings.password or ""

    post_response = client.post(login_url, data=payload)
    if post_response.status_code in {401, 403}:
        raise AuthError(
            f"login rejected with HTTP {post_response.status_code}",
            login_url=login_url,
        )
    if _looks_like_login_page(post_response.text, settings, post_response.url):
        raise AuthError("login form still present after POST", login_url=login_url)


def _browser_login(client: httpx.Client, settings: Settings) -> None:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as exc:
        raise AuthError(
            "browser auth requires Playwright; install with: "
            "pip install -r requirements-browser.txt"
        ) from exc

    login_url = str(settings.login_url)
    user_agent = client.headers.get("User-Agent")

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        try:
            context = browser.new_context(user_agent=user_agent)
            page = context.new_page()
            page.goto(login_url, wait_until="domcontentloaded")
            page.fill(settings.login_username_selector, settings.username or "")
            page.fill(settings.login_password_selector, settings.password or "")
            page.click(settings.login_submit_selector)
            page.wait_for_load_state("networkidle")

            final_url = page.url
            html = page.content()
            if _looks_like_login_page(html, settings, final_url):
                raise AuthError("browser login did not leave login page", login_url=login_url)

            if settings.login_success_url and settings.login_success_url not in final_url:
                raise AuthError(
                    f"expected URL containing {settings.login_success_url!r}, got {final_url!r}",
                    login_url=login_url,
                )

            for cookie in context.cookies():
                client.cookies.set(
                    cookie["name"],
                    cookie["value"],
                    domain=cookie.get("domain"),
                    path=cookie.get("path", "/"),
                )
        finally:
            browser.close()


def _verify_session(client: httpx.Client, settings: Settings) -> None:
    probe_url = str(settings.base_url)
    response = client.get(probe_url)

    if response.status_code in {401, 403}:
        raise AuthError(
            f"session probe returned HTTP {response.status_code}",
            login_url=str(settings.login_url) if settings.login_url else None,
        )

    if settings.login_url and _looks_like_login_page(
        response.text,
        settings,
        response.url,
    ):
        raise AuthError(
            "session probe still shows login page",
            login_url=str(settings.login_url),
        )

    if settings.login_success_url and settings.login_success_url not in str(response.url):
        _LOG.debug(
            "login_success_url not matched on probe (non-fatal)",
            extra={"url": str(response.url)},
        )


def _extract_form_payload(html: str, settings: Settings) -> dict[str, str]:
    tree = HTMLParser(html)
    form = tree.css_first(settings.login_form_selector)
    if form is None:
        raise AuthError(f"login form not found: {settings.login_form_selector}")

    payload: dict[str, str] = {}
    for node in form.css("input"):
        name = node.attributes.get("name")
        if not name:
            continue
        input_type = (node.attributes.get("type") or "text").lower()
        if input_type in {"submit", "button", "image", "file"}:
            continue
        payload[name] = node.attributes.get("value") or ""
    return payload


def _username_field_name(settings: Settings, html: str) -> str:
    tree = HTMLParser(html)
    node = tree.css_first(settings.login_username_selector)
    if node is None:
        raise AuthError(f"username field not found: {settings.login_username_selector}")
    name = node.attributes.get("name")
    if not name:
        raise AuthError(f"username field has no name attribute: {settings.login_username_selector}")
    return name


def _password_field_name(settings: Settings, html: str) -> str:
    tree = HTMLParser(html)
    node = tree.css_first(settings.login_password_selector)
    if node is None:
        raise AuthError(f"password field not found: {settings.login_password_selector}")
    name = node.attributes.get("name")
    if not name:
        raise AuthError(f"password field has no name attribute: {settings.login_password_selector}")
    return name


def _looks_like_login_page(html: str, settings: Settings, url: httpx.URL | str) -> bool:
    tree = HTMLParser(html)
    if tree.css_first(settings.login_form_selector) is None:
        return False
    has_username = tree.css_first(settings.login_username_selector) is not None
    has_password = tree.css_first(settings.login_password_selector) is not None
    return has_username and has_password
