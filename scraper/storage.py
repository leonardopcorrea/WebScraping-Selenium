"""Persist validated records to Excel, CSV, or JSON."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from scraper.models import HockeyTeamRecord

COLUMNS = [
    "Team Name",
    "Year",
    "Wins",
    "Losses",
    "OT Losses",
    "Win %",
    "Goals For (GF)",
    "Goals Against (GA)",
    "+ / -",
    "Source URL",
    "Page",
]


def records_to_frame(records: list[HockeyTeamRecord]) -> pd.DataFrame:
    rows = [
        [
            rec.team_name,
            rec.year,
            rec.wins,
            rec.losses,
            rec.ot_losses,
            rec.win_pct,
            rec.goals_for,
            rec.goals_against,
            rec.plus_minus,
            rec.source_url,
            rec.page_num,
        ]
        for rec in records
    ]
    return pd.DataFrame(rows, columns=COLUMNS)


def write_excel(records: list[HockeyTeamRecord], path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    records_to_frame(records).to_excel(path, index=False)
    return path


def write_csv(records: list[HockeyTeamRecord], path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    records_to_frame(records).to_csv(path, index=False)
    return path


def write_json(records: list[HockeyTeamRecord], path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = [record.model_dump() for record in records]
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return path


def resolve_output_format(path: Path, explicit: str | None = None) -> str:
    if explicit:
        return explicit
    suffix = path.suffix.lower()
    if suffix == ".csv":
        return "csv"
    if suffix == ".json":
        return "json"
    return "xlsx"


def write_output(
    records: list[HockeyTeamRecord],
    path: Path,
    *,
    output_format: str | None = None,
) -> Path:
    fmt = resolve_output_format(path, output_format)
    if fmt == "csv":
        return write_csv(records, path)
    if fmt == "json":
        return write_json(records, path)
    return write_excel(records, path)
