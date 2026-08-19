"""Validated records extracted from the hockey table."""

from pydantic import BaseModel, ConfigDict, Field, field_validator


class HockeyTeamRecord(BaseModel):
    """One NHL team season row from scrapethissite forms table."""

    model_config = ConfigDict(str_strip_whitespace=True)

    team_name: str = Field(min_length=1)
    year: int = Field(ge=1900, le=2100)
    wins: int = Field(ge=0)
    losses: int = Field(ge=0)
    ot_losses: int | None = None
    win_pct: float | None = Field(default=None, ge=0.0, le=1.0)
    goals_for: int = Field(ge=0)
    goals_against: int = Field(ge=0)
    plus_minus: int
    source_url: str
    page_num: int = Field(ge=1)

    @field_validator("ot_losses", mode="before")
    @classmethod
    def empty_ot_losses(cls, value: object) -> object:
        if value in ("", None, "-"):
            return None
        return value

    @field_validator("win_pct", mode="before")
    @classmethod
    def empty_win_pct(cls, value: object) -> object:
        if value in ("", None, "-"):
            return None
        return value
