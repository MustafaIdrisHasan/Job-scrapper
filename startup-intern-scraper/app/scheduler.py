"""Scheduling helpers for repeating scraper runs."""

from __future__ import annotations

import logging
import time

import schedule

from .config import Settings

LOGGER = logging.getLogger(__name__)


def run_schedule(run_once, settings: Settings) -> None:
    """Execute `run_once` immediately, then every two days."""
    LOGGER.info("Starting schedule loop (every 2 days).")
    run_once()

    job = schedule.every(2).days.do(run_once)

    while True:
        schedule.run_pending()
        time.sleep(5)

