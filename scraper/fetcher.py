"""HTTP fetch with retries, exponential backoff, and status-aware errors."""

from __future__ import annotations

import random
import time
from collections.abc import Iterator
from typing import Final

import httpx

from scraper.config import Settings
from scraper.exceptions import FetchError, RateLimitedError
from scraper.logging_setup import logger_for
from scraper.stealth import browser_headers, jitter_delay

RETRYABLE_STATUS: Final[set[int]] = {408, 425, 429, 500, 502, 503, 504}


class HttpFetcher:
    """Synchronous HTTP client with connection reuse and bounded retries."""

    def __init__(self, settings: Settings, *, client: httpx.Client | None = None) -> None:
        self._settings = settings
        if client is not None:
            self._client = client
            return
        client_kwargs: dict = {
            "headers": browser_headers(settings.user_agent),
            "timeout": httpx.Timeout(settings.request_timeout_s),
            "follow_redirects": True,
        }
        if settings.proxy_url:
            client_kwargs["proxy"] = settings.proxy_url
        self._client = httpx.Client(**client_kwargs)

    @property
    def client(self) -> httpx.Client:
        """Underlying httpx client (shared cookie jar and headers)."""
        return self._client

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> HttpFetcher:
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    def get_text(self, url: str, *, page: int | None = None) -> str:
        """GET a URL and return decoded HTML, retrying transient failures."""
        log = logger_for(url=url, page=page)
        last_error: Exception | None = None

        for attempt in range(self._settings.max_retries + 1):
            try:
                response = self._client.get(url)
            except httpx.TimeoutException as exc:
                last_error = exc
                self._backoff(attempt, log, reason="timeout")
                continue
            except httpx.TransportError as exc:
                last_error = exc
                self._backoff(attempt, log, reason=type(exc).__name__)
                continue

            if response.status_code == 429:
                retry_after = self._retry_after_seconds(response)
                log.warning(
                    "rate limited",
                    extra={"status": 429, "retry_after_s": retry_after},
                )
                if attempt >= self._settings.max_retries:
                    raise RateLimitedError(url, "HTTP 429 after retries", status_code=429)
                time.sleep(retry_after)
                continue

            if response.status_code in RETRYABLE_STATUS:
                last_error = FetchError(
                    url,
                    f"HTTP {response.status_code}",
                    status_code=response.status_code,
                )
                self._backoff(attempt, log, reason=f"HTTP {response.status_code}")
                continue

            if response.status_code >= 400:
                raise FetchError(
                    url,
                    f"HTTP {response.status_code}",
                    status_code=response.status_code,
                )

            return response.text

        raise FetchError(url, f"retries exhausted: {last_error}") from last_error

    def iter_listing_urls(self) -> Iterator[tuple[int, str]]:
        """Yield (page_number, url) until max_pages, if set."""
        page = 1
        while True:
            if self._settings.max_pages and page > self._settings.max_pages:
                return
            yield page, self._page_url(page)
            page += 1

    def _page_url(self, page: int) -> str:
        base = str(self._settings.base_url)
        separator = "&" if "?" in base else "?"
        return f"{base}{separator}page_num={page}&per_page={self._settings.page_size}"

    def _backoff(self, attempt: int, log, *, reason: str) -> None:
        if attempt >= self._settings.max_retries:
            return
        delay = min(30.0, (2**attempt) + random.uniform(0, 0.75))
        log.warning(
            "retrying fetch",
            extra={"attempt": attempt + 1, "reason": reason, "sleep_s": round(delay, 2)},
        )
        time.sleep(delay)

    @staticmethod
    def _retry_after_seconds(response: httpx.Response) -> float:
        header = response.headers.get("Retry-After")
        if header and header.isdigit():
            return min(float(header), 60.0)
        return 5.0 + random.uniform(0, 2.0)


def polite_pause(settings: Settings) -> None:
    time.sleep(jitter_delay(settings.min_delay_s, settings.max_delay_s))
