"""Shared pytest fixtures."""

from pathlib import Path

import pytest

from scraper.config import Settings

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def listing_html() -> str:
    return (FIXTURES / "listing_page.html").read_text(encoding="utf-8")


@pytest.fixture
def empty_page_html() -> str:
    return (FIXTURES / "empty_page.html").read_text(encoding="utf-8")


@pytest.fixture
def no_table_html() -> str:
    return (FIXTURES / "no_table.html").read_text(encoding="utf-8")


@pytest.fixture
def fast_settings() -> Settings:
    return Settings(
        _env_file=None,
        max_pages=1,
        min_delay_s=0,
        max_delay_s=0,
        max_retries=2,
        request_timeout_s=5,
    )
