"""Domain-specific scrape failures."""


class ScrapeError(Exception):
    """Base error for recoverable scrape failures."""


class FetchError(ScrapeError):
    """HTTP/network failure after retries were exhausted."""

    def __init__(self, url: str, message: str, status_code: int | None = None) -> None:
        super().__init__(f"{url}: {message}")
        self.url = url
        self.status_code = status_code


class ParseError(ScrapeError):
    """DOM/selector mismatch that prevents extracting a page."""

    def __init__(self, url: str, message: str) -> None:
        super().__init__(f"{url}: {message}")
        self.url = url


class AuthError(ScrapeError):
    """Login or session setup failed before scraping started."""

    def __init__(self, message: str, *, login_url: str | None = None) -> None:
        super().__init__(message)
        self.login_url = login_url


class RateLimitedError(FetchError):
    """Server asked the client to slow down (HTTP 429)."""
