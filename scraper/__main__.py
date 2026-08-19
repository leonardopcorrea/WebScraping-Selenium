"""Orchestrate fetch → parse → store with per-page failure isolation."""

from __future__ import annotations

import argparse
import time
from pathlib import Path

from scraper.auth import authenticate
from scraper.config import Settings
from scraper.exceptions import AuthError, FetchError, ParseError, RateLimitedError
from scraper.fetcher import HttpFetcher, polite_pause
from scraper.logging_setup import configure_logging, logger_for
from scraper.models import HockeyTeamRecord
from scraper.parser import parse_listing
from scraper.storage import write_output


def run(settings: Settings | None = None) -> list[HockeyTeamRecord]:
    settings = settings or Settings()
    log = configure_logging(settings.log_level)
    started = time.perf_counter()
    records: list[HockeyTeamRecord] = []
    consecutive_empty = 0

    with HttpFetcher(settings) as fetcher:
        try:
            authenticate(fetcher.client, settings)
        except AuthError as exc:
            log.error("authentication failed: %s", exc)
            raise

        for page, url in fetcher.iter_listing_urls():
            page_log = logger_for(url=url, page=page)
            polite_pause(settings)
            try:
                html = fetcher.get_text(url, page=page)
                page_records = parse_listing(html, url=url, page=page)
            except RateLimitedError:
                page_log.error("giving up after rate limit")
                raise
            except FetchError as exc:
                page_log.error("page fetch failed", extra={"status": exc.status_code})
                continue
            except ParseError as exc:
                page_log.error("page parse failed: %s", exc)
                continue

            if not page_records:
                consecutive_empty += 1
                if consecutive_empty >= 2 or settings.max_pages == 0:
                    page_log.info("stopping pagination")
                    break
                continue

            consecutive_empty = 0
            records.extend(page_records)
            page_log.info("page extracted", extra={"rows": len(page_records), "total": len(records)})

    elapsed = time.perf_counter() - started
    output = write_output(
        records,
        settings.output_path,
        output_format=settings.output_format,
    )
    log.info(
        "scrape complete rows=%s elapsed_s=%.2f output=%s",
        len(records),
        elapsed,
        output,
    )
    return records


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Scrape the paginated hockey teams table (httpx + CSS parse).",
    )
    parser.add_argument(
        "--max-pages",
        type=int,
        default=None,
        help="Stop after N pages (0 = until empty page). Overrides MAX_PAGES in .env.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Output file path. Overrides OUTPUT_PATH in .env.",
    )
    parser.add_argument(
        "--format",
        dest="output_format",
        choices=["xlsx", "csv", "json"],
        default=None,
        help="Output format. Defaults to the file extension of --output / OUTPUT_PATH.",
    )
    return parser


def settings_from_args(args: argparse.Namespace) -> Settings:
    settings = Settings()
    overrides: dict = {}
    if args.max_pages is not None:
        overrides["max_pages"] = args.max_pages
    if args.output is not None:
        overrides["output_path"] = args.output
    if args.output_format is not None:
        overrides["output_format"] = args.output_format
    if overrides:
        return settings.model_copy(update=overrides)
    return settings


def main(argv: list[str] | None = None) -> None:
    args = build_parser().parse_args(argv)
    run(settings_from_args(args))


if __name__ == "__main__":
    main()
