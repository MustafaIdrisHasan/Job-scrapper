"""Scraper orchestration and HTTP helper utilities."""

from __future__ import annotations

import logging
import random
import time
from dataclasses import dataclass
from typing import Callable, Iterable, List, Tuple
from urllib.parse import urlparse

import requests
from requests.adapters import HTTPAdapter, Retry

from ..config import Settings
from ..models import InternshipListing
from . import startup_jobs, wellfound, yc

LOGGER = logging.getLogger(__name__)


def scrape_all(settings: Settings) -> List[InternshipListing]:
    """Execute all configured scrapers and return combined listings."""
    client = HttpClient(settings)
    scrapers: List[Tuple[str, Callable[[Settings, "HttpClient"], List[InternshipListing]]]] = [
        ("yc", yc.scrape),
        ("indeed", startup_jobs.scrape),  # renamed from startup_jobs to indeed
    ]
    if settings.enable_wellfound:
        scrapers.append(("wellfound", wellfound.scrape))

    all_listings: List[InternshipListing] = []
    for name, scraper_fn in scrapers:
        try:
            LOGGER.info("Scraping %s...", name)
            listings = scraper_fn(settings, client)
            all_listings.extend(listings)
            LOGGER.info("Fetched %d records from %s.", len(listings), name)
        except Exception as exc:  # noqa: BLE001
            LOGGER.error("Failed to scrape %s: %s", name, exc)
    return all_listings


@dataclass
class HttpClient:
    """Wrapper around requests.Session with politeness controls."""

    settings: Settings

    def __post_init__(self) -> None:
        self._session = requests.Session()
        retries = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=(429, 500, 502, 503, 504),
            allowed_methods=("GET", "HEAD"),
        )
        adapter = HTTPAdapter(max_retries=retries)
        self._session.mount("https://", adapter)
        self._session.mount("http://", adapter)
        self._session.headers.update(
            {
                "User-Agent": self.settings.user_agent,
                "Accept-Language": "en-US,en;q=0.9",
                "Referer": "https://www.google.com/",
            }
        )
        self._last_request: dict[str, float] = {}

    def get(self, url: str, **kwargs) -> requests.Response:
        domain = urlparse(url).netloc
        self._respect_rate_limit(domain)
        self._random_delay()
        try:
            response = self._session.get(url, timeout=20, **kwargs)
            response.raise_for_status()
            self._last_request[domain] = time.time()
            return response
        except Exception:
            LOGGER.debug("Request to %s failed.", url)
            raise

    def _random_delay(self) -> None:
        delay = random.uniform(
            self.settings.scrape_delay_min_seconds,
            self.settings.scrape_delay_max_seconds,
        )
        time.sleep(delay)

    def _respect_rate_limit(self, domain: str) -> None:
        minimum_gap = self.settings.rate_limits.get(domain, 0.0)
        if minimum_gap <= 0:
            return
        now = time.time()
        last = self._last_request.get(domain)
        if last is None:
            self._last_request[domain] = now
            return
        elapsed = now - last
        if elapsed < minimum_gap:
            time.sleep(minimum_gap - elapsed)
        self._last_request[domain] = time.time()
