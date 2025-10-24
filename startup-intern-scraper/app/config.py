"""Configuration loading for the internship scraper."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Optional

from dotenv import load_dotenv


@dataclass
class Settings:
    """Runtime configuration derived from environment variables."""

    gmail_sender: Optional[str] = None
    gmail_app_password: Optional[str] = None
    gmail_recipient: Optional[str] = None
    scrape_delay_min_seconds: float = 2.0
    scrape_delay_max_seconds: float = 6.0
    user_agent: str = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    )
    enable_wellfound: bool = False
    run_debug: bool = False
    rate_limits: Dict[str, float] = field(default_factory=dict)
    output_dir: Path = Path("out")
    # Role filtering options
    job_type: Optional[str] = None  # "internship", "fulltime", "contract", etc.
    role_category: Optional[str] = None  # "backend", "frontend", "fullstack", "data", "ai", etc.
    keywords: Optional[str] = None  # Custom keywords to search for


def load_settings(env_path: Optional[Path] = None) -> Settings:
    """Read configuration from .env if present and return Settings."""

    if env_path is None:
        env_path = Path(".env")
    load_dotenv(env_path)

    settings = Settings()
    settings.gmail_sender = _get_env("GMAIL_SENDER")
    settings.gmail_app_password = _get_env("GMAIL_APP_PASSWORD")
    settings.gmail_recipient = _get_env("GMAIL_RECIPIENT")
    settings.scrape_delay_min_seconds = float(
        _get_env("SCRAPE_DELAY_MIN_SECONDS", settings.scrape_delay_min_seconds)
    )
    settings.scrape_delay_max_seconds = float(
        _get_env("SCRAPE_DELAY_MAX_SECONDS", settings.scrape_delay_max_seconds)
    )
    settings.user_agent = _get_env("USER_AGENT", settings.user_agent)
    settings.enable_wellfound = _get_env("ENABLE_WELLFOUND", "false").lower() == "true"
    rate_limits_raw = _get_env("RATE_LIMITS", "")
    settings.rate_limits = _parse_rate_limits(rate_limits_raw)
    output_dir = _get_env("OUTPUT_DIR")
    if output_dir:
        settings.output_dir = Path(output_dir)
    settings.run_debug = _get_env("DEBUG", "false").lower() == "true"
    
    # Role filtering settings
    settings.job_type = _get_env("JOB_TYPE")
    settings.role_category = _get_env("ROLE_CATEGORY")
    settings.keywords = _get_env("KEYWORDS")
    
    return settings


def _get_env(key: str, default: Optional[str] = None) -> Optional[str]:
    from os import environ

    return environ.get(key, default)


def _parse_rate_limits(raw: str) -> Dict[str, float]:
    """Parse comma-separated `domain=seconds` pairs."""
    limits: Dict[str, float] = {}
    if not raw:
        return limits
    for item in raw.split(","):
        if "=" not in item:
            continue
        domain, value = item.split("=", 1)
        domain = domain.strip()
        try:
            limits[domain] = float(value.strip())
        except ValueError:
            continue
    return limits

