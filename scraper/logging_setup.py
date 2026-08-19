"""Structured logging with URL/page context."""

import logging
import sys


class ContextAdapter(logging.LoggerAdapter):
    """Injects scrape context (url, page) into every log record."""

    def process(self, msg: str, kwargs: dict) -> tuple[str, dict]:
        extra = dict(self.extra)
        extra.update(kwargs.get("extra") or {})
        kwargs["extra"] = extra
        context = " ".join(f"{key}={value}" for key, value in extra.items() if value is not None)
        if context:
            return f"{msg} | {context}", kwargs
        return msg, kwargs


def configure_logging(level: str) -> logging.Logger:
    """Configure a single stderr logger. Call once from the entrypoint."""
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
        stream=sys.stderr,
        force=True,
    )
    return logging.getLogger("scraper")


def logger_for(*, url: str | None = None, page: int | None = None) -> ContextAdapter:
    return ContextAdapter(logging.getLogger("scraper"), {"url": url, "page": page})
