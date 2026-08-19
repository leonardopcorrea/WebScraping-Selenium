"""Realistic browser-like request identity without claiming undetectability."""

from __future__ import annotations

import random

_CHROME_VERSIONS = ("128.0.6613.120", "129.0.6668.90", "131.0.6778.86")


def default_user_agent() -> str:
    version = random.choice(_CHROME_VERSIONS)
    return (
        f"Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        f"AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{version} Safari/537.36"
    )


def browser_headers(user_agent: str | None = None) -> dict[str, str]:
    """Headers that belong together as a desktop Chrome session."""
    ua = user_agent or default_user_agent()
    return {
        "User-Agent": ua,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9,pt-BR;q=0.8",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "Sec-Fetch-User": "?1",
        "Cache-Control": "max-age=0",
    }


def jitter_delay(min_s: float, max_s: float) -> float:
    """Humanized pause. Uniform jitter beats a fixed sleep for rate shaping."""
    if max_s <= 0:
        return 0.0
    lo, hi = (min_s, max_s) if min_s <= max_s else (max_s, min_s)
    return random.uniform(lo, hi)
