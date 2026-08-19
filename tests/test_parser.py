"""Parser tests using offline HTML fixtures."""

import pytest

from scraper.exceptions import ParseError
from scraper.parser import parse_listing


def test_parse_listing_extracts_rows(listing_html: str) -> None:
    records = parse_listing(listing_html, url="https://example.test/?page=1", page=1)

    assert len(records) == 2
    assert records[0].team_name == "Boston Bruins"
    assert records[0].year == 1990
    assert records[0].wins == 44
    assert records[0].ot_losses is None
    assert records[0].win_pct == pytest.approx(0.647)
    assert records[0].source_url == "https://example.test/?page=1"
    assert records[0].page_num == 1

    assert records[1].team_name == "Buffalo Sabres"
    assert records[1].ot_losses is None
    assert records[1].plus_minus == -9


def test_parse_listing_empty_page_returns_empty_list(empty_page_html: str) -> None:
    records = parse_listing(empty_page_html, url="https://example.test/?page=99", page=99)
    assert records == []


def test_parse_listing_missing_table_raises(no_table_html: str) -> None:
    with pytest.raises(ParseError, match="table.table is missing"):
        parse_listing(no_table_html, url="https://example.test/", page=1)
