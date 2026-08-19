"""Storage helpers and multi-format export."""

import json
from pathlib import Path

import pandas as pd
import pytest

from scraper.models import HockeyTeamRecord
from scraper.storage import resolve_output_format, write_csv, write_json, write_output


@pytest.fixture
def sample_records() -> list[HockeyTeamRecord]:
    return [
        HockeyTeamRecord.model_validate(
            {
                "team_name": "Boston Bruins",
                "year": 1990,
                "wins": 44,
                "losses": 24,
                "ot_losses": None,
                "win_pct": 0.647,
                "goals_for": 273,
                "goals_against": 223,
                "plus_minus": 50,
                "source_url": "https://example.test/?page=1",
                "page_num": 1,
            }
        )
    ]


def test_resolve_output_format_from_extension() -> None:
    assert resolve_output_format(Path("out/data.csv")) == "csv"
    assert resolve_output_format(Path("out/data.json")) == "json"
    assert resolve_output_format(Path("out/data.xlsx")) == "xlsx"


def test_resolve_output_format_explicit_overrides_extension() -> None:
    assert resolve_output_format(Path("out/data.xlsx"), "json") == "json"


def test_write_csv_and_json(tmp_path: Path, sample_records) -> None:
    csv_path = write_csv(sample_records, tmp_path / "teams.csv")
    json_path = write_json(sample_records, tmp_path / "teams.json")

    csv_df = pd.read_csv(csv_path)
    assert csv_df.iloc[0]["Team Name"] == "Boston Bruins"

    payload = json.loads(json_path.read_text(encoding="utf-8"))
    assert payload[0]["team_name"] == "Boston Bruins"
    assert payload[0]["year"] == 1990


def test_write_output_dispatches_by_format(tmp_path: Path, sample_records) -> None:
    path = write_output(sample_records, tmp_path / "teams.json")
    assert path.suffix == ".json"
    assert path.exists()
