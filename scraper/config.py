"""Runtime configuration loaded from environment variables."""

from pathlib import Path
from typing import Literal

from pydantic import Field, HttpUrl, ValidationInfo, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

OutputFormat = Literal["xlsx", "csv", "json"]
AuthMode = Literal["off", "cookie", "form", "browser"]


class Settings(BaseSettings):
    """Scraper settings. Secrets and tunables live in `.env`, not in source."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    base_url: HttpUrl = Field(
        default="https://www.scrapethissite.com/pages/forms/",
        description="Paginated listing URL without query string.",
    )
    page_size: int = Field(default=25, ge=1, le=200)
    max_pages: int = Field(
        default=0,
        ge=0,
        description="Hard cap on pages. 0 means follow pagination until empty.",
    )
    output_path: Path = Field(default=Path("output/hockey_teams.xlsx"))
    output_format: OutputFormat | None = Field(
        default=None,
        description="Export format. When unset, inferred from OUTPUT_PATH extension.",
    )
    request_timeout_s: float = Field(default=20.0, gt=0)
    max_retries: int = Field(default=4, ge=0, le=10)
    min_delay_s: float = Field(default=0.4, ge=0)
    max_delay_s: float = Field(default=1.2, ge=0)
    user_agent: str | None = Field(default=None)
    proxy_url: str | None = Field(default=None)
    log_level: str = Field(default="INFO")

    auth_mode: AuthMode = Field(
        default="off",
        description="Authentication strategy: off, cookie, form, or browser.",
    )
    login_url: HttpUrl | None = Field(
        default=None,
        description="Login page URL for form/browser modes.",
    )
    username: str | None = Field(default=None)
    password: str | None = Field(default=None)
    cookie_header: str | None = Field(
        default=None,
        description="Raw Cookie header value for AUTH_MODE=cookie.",
    )
    auth_bearer: str | None = Field(
        default=None,
        description="Bearer token for AUTH_MODE=cookie (Authorization header).",
    )
    login_form_selector: str = Field(default="form")
    login_username_selector: str = Field(default="#username")
    login_password_selector: str = Field(default="#password")
    login_submit_selector: str = Field(default='button[type="submit"]')
    login_success_url: str | None = Field(
        default=None,
        description="Optional substring expected in URL after successful login.",
    )

    @field_validator("max_delay_s")
    @classmethod
    def delay_range_is_valid(cls, value: float, info: ValidationInfo) -> float:
        min_delay = info.data.get("min_delay_s", 0.0)
        if value < min_delay:
            raise ValueError("MAX_DELAY_S must be >= MIN_DELAY_S")
        return value

    @field_validator("login_url")
    @classmethod
    def login_url_required_for_auth(cls, value: HttpUrl | None, info: ValidationInfo) -> HttpUrl | None:
        mode = info.data.get("auth_mode", "off")
        if mode in {"form", "browser"} and value is None:
            raise ValueError("LOGIN_URL is required when AUTH_MODE is form or browser")
        return value

    @field_validator("username")
    @classmethod
    def username_required_for_auth(cls, value: str | None, info: ValidationInfo) -> str | None:
        mode = info.data.get("auth_mode", "off")
        if mode in {"form", "browser"} and not value:
            raise ValueError("USERNAME is required when AUTH_MODE is form or browser")
        return value

    @field_validator("password")
    @classmethod
    def password_required_for_auth(cls, value: str | None, info: ValidationInfo) -> str | None:
        mode = info.data.get("auth_mode", "off")
        if mode in {"form", "browser"} and not value:
            raise ValueError("PASSWORD is required when AUTH_MODE is form or browser")
        return value

    @field_validator("cookie_header")
    @classmethod
    def cookie_or_bearer_required(cls, value: str | None, info: ValidationInfo) -> str | None:
        mode = info.data.get("auth_mode", "off")
        bearer = info.data.get("auth_bearer")
        if mode == "cookie" and not value and not bearer:
            raise ValueError("COOKIE_HEADER or AUTH_BEARER is required when AUTH_MODE=cookie")
        return value
