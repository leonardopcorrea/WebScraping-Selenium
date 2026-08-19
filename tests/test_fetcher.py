"""Fetcher retry behavior with httpx.MockTransport."""

import httpx
import pytest

from scraper.exceptions import FetchError, RateLimitedError
from scraper.fetcher import HttpFetcher


def test_get_text_retries_transient_503(fast_settings) -> None:
    attempts = {"count": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        attempts["count"] += 1
        if attempts["count"] == 1:
            return httpx.Response(503)
        return httpx.Response(200, text="<html>ok</html>")

    transport = httpx.MockTransport(handler)
    with httpx.Client(transport=transport) as client:
        fetcher = HttpFetcher(fast_settings, client=client)
        text = fetcher.get_text("https://example.test/page", page=1)

    assert text == "<html>ok</html>"
    assert attempts["count"] == 2


def test_get_text_raises_after_exhausted_retries(fast_settings) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(503)

    transport = httpx.MockTransport(handler)
    with httpx.Client(transport=transport) as client:
        fetcher = HttpFetcher(fast_settings, client=client)
        with pytest.raises(FetchError, match="retries exhausted"):
            fetcher.get_text("https://example.test/fail", page=1)


def test_get_text_raises_on_definitive_404(fast_settings) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(404)

    transport = httpx.MockTransport(handler)
    with httpx.Client(transport=transport) as client:
        fetcher = HttpFetcher(fast_settings, client=client)
        with pytest.raises(FetchError, match="HTTP 404") as exc_info:
            fetcher.get_text("https://example.test/missing", page=1)

    assert exc_info.value.status_code == 404


def test_get_text_rate_limit_then_success(fast_settings, monkeypatch) -> None:
    attempts = {"count": 0}
    sleeps: list[float] = []

    def handler(request: httpx.Request) -> httpx.Response:
        attempts["count"] += 1
        if attempts["count"] == 1:
            return httpx.Response(429, headers={"Retry-After": "1"})
        return httpx.Response(200, text="done")

    monkeypatch.setattr("scraper.fetcher.time.sleep", lambda s: sleeps.append(s))

    transport = httpx.MockTransport(handler)
    with httpx.Client(transport=transport) as client:
        fetcher = HttpFetcher(fast_settings, client=client)
        text = fetcher.get_text("https://example.test/rate", page=1)

    assert text == "done"
    assert attempts["count"] == 2
    assert sleeps == [1.0]


def test_get_text_rate_limit_exhausted_raises(fast_settings, monkeypatch) -> None:
    monkeypatch.setattr("scraper.fetcher.time.sleep", lambda _: None)

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(429, headers={"Retry-After": "1"})

    transport = httpx.MockTransport(handler)
    with httpx.Client(transport=transport) as client:
        fetcher = HttpFetcher(fast_settings, client=client)
        with pytest.raises(RateLimitedError):
            fetcher.get_text("https://example.test/limit", page=1)
