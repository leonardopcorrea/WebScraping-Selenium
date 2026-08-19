"""CLI argument parsing."""

import argparse
from pathlib import Path

from scraper.__main__ import build_parser, settings_from_args


def test_build_parser_accepts_overrides() -> None:
    parser = build_parser()
    args = parser.parse_args(["--max-pages", "3", "--output", "out/t.csv", "--format", "csv"])

    assert args.max_pages == 3
    assert args.output == Path("out/t.csv")
    assert args.output_format == "csv"


def test_settings_from_args_overrides_env(monkeypatch) -> None:
    monkeypatch.setenv("MAX_PAGES", "10")
    monkeypatch.setenv("OUTPUT_PATH", "output/default.xlsx")

    args = build_parser().parse_args(["--max-pages", "2"])
    settings = settings_from_args(args)

    assert settings.max_pages == 2
    assert settings.output_path == Path("output/default.xlsx")
