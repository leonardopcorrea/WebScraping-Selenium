"""DOM extraction using CSS classes, not brittle absolute XPath."""

from __future__ import annotations

from pydantic import ValidationError
from selectolax.parser import HTMLParser, Node

from scraper.exceptions import ParseError
from scraper.logging_setup import logger_for
from scraper.models import HockeyTeamRecord

_FIELD_SELECTORS = {
    "team_name": "td.name",
    "year": "td.year",
    "wins": "td.wins",
    "losses": "td.losses",
    "ot_losses": "td.ot-losses",
    "win_pct": "td.pct",
    "goals_for": "td.gf",
    "goals_against": "td.ga",
    "plus_minus": "td.diff",
}


def parse_listing(html: str, *, url: str, page: int) -> list[HockeyTeamRecord]:
    """Parse one listing page. Empty result means pagination is exhausted."""
    log = logger_for(url=url, page=page)
    tree = HTMLParser(html)
    rows = tree.css("table.table tr.team")
    if not rows:
        if tree.css_first("table.table") is None:
            raise ParseError(url, "expected table.table is missing (selector drift or block page)")
        log.info("no team rows on page")
        return []

    records: list[HockeyTeamRecord] = []
    skipped = 0
    for row in rows:
        payload = _row_payload(row)
        if payload is None:
            skipped += 1
            continue
        try:
            records.append(
                HockeyTeamRecord.model_validate(
                    {**payload, "source_url": url, "page_num": page}
                )
            )
        except ValidationError as exc:
            skipped += 1
            log.warning("row failed validation", extra={"errors": exc.error_count()})

    if skipped:
        log.warning("skipped invalid rows", extra={"skipped": skipped, "kept": len(records)})
    return records


def _row_payload(row: Node) -> dict[str, str] | None:
    payload: dict[str, str] = {}
    for field, selector in _FIELD_SELECTORS.items():
        node = row.css_first(selector)
        if node is None:
            return None
        payload[field] = node.text(strip=True)
    if not payload["team_name"]:
        return None
    return payload
