"""Scraper parsing smoke tests with static HTML fixtures."""

from __future__ import annotations

import unittest

from app.config import Settings
from app.scrapers import startup_jobs, yc


class FakeResponse:
    def __init__(self, text: str):
        self.text = text

    def raise_for_status(self) -> None:  # noqa: D401
        """Mimic requests.Response.raise_for_status."""
        return None


class FakeHttpClient:
    def __init__(self, pages: dict[str, str]):
        self.pages = pages

    def get(self, url: str, **kwargs) -> FakeResponse:  # noqa: D401
        """Return fake HTML responses."""
        try:
            return FakeResponse(self.pages[url])
        except KeyError:
            raise AssertionError(f"No fixture for URL {url}") from None


class ScraperParsingTest(unittest.TestCase):
    def setUp(self) -> None:
        self.settings = Settings(
            gmail_sender=None,
            gmail_app_password=None,
            gmail_recipient=None,
            scrape_delay_min_seconds=0.0,
            scrape_delay_max_seconds=0.0,
            user_agent="test-agent",
            enable_wellfound=False,
            run_debug=False,
            rate_limits={},
        )

    def test_yc_scraper_parses_fixture(self) -> None:
        original_list_urls = yc.LIST_URLS
        original_base = yc.BASE_URL
        yc.LIST_URLS = ["https://fake.yc/list"]
        yc.BASE_URL = "https://fake.yc"
        try:
            client = FakeHttpClient(
                {
                    "https://fake.yc/list": YC_LISTING_HTML,
                    "https://fake.yc/jobs/123": YC_DETAIL_HTML,
                }
            )
            listings = yc.scrape(self.settings, client)  # type: ignore[arg-type]
            self.assertTrue(listings, "YC scraper should parse at least one item.")
            first = listings[0]
            self.assertEqual(first.company, "Alpha Labs")
            self.assertIn("Python", first.responsibilities)
        finally:
            yc.LIST_URLS = original_list_urls
            yc.BASE_URL = original_base

    def test_startup_jobs_scraper_parses_fixture(self) -> None:
        original_start_url = startup_jobs.START_URL
        original_base = startup_jobs.BASE_URL
        startup_jobs.START_URL = "https://fake.startup.jobs/list"
        startup_jobs.BASE_URL = "https://fake.startup.jobs"
        try:
            client = FakeHttpClient(
                {
                    "https://fake.startup.jobs/list": STARTUP_LISTING_HTML,
                    "https://fake.startup.jobs/job/456": STARTUP_DETAIL_HTML,
                }
            )
            listings = startup_jobs.scrape(self.settings, client)  # type: ignore[arg-type]
            self.assertTrue(
                listings, "Startup Jobs scraper should parse at least one item."
            )
            first = listings[0]
            self.assertEqual(first.role_title, "Data Science Intern")
            self.assertIn("Salary: $20/hr", first.pay)
        finally:
            startup_jobs.START_URL = original_start_url
            startup_jobs.BASE_URL = original_base


YC_LISTING_HTML = """
<html>
  <body>
    <div class="role-card">
      <a class="role-card__link" href="/jobs/123">View</a>
      <div class="role-card__company">Alpha Labs</div>
      <div class="role-card__title">Software Intern</div>
      <div class="role-card__location">Remote</div>
      <div class="role-card__salary">$30/hr</div>
      <time datetime="2025-05-01"></time>
    </div>
  </body>
</html>
"""

YC_DETAIL_HTML = """
<html>
  <body>
    <section id="job-description">
      <p>Build backend services for customers.</p>
      <li>Collaborate using Python and REST APIs.</li>
    </section>
  </body>
</html>
"""

STARTUP_LISTING_HTML = """
<html>
  <body>
    <ul class="jobs-list">
      <li>
        <a class="job-listing__link" href="/job/456">View</a>
        <div class="job-listing__title">Data Science Intern</div>
        <div class="job-listing__company">Beta Analytics</div>
        <div class="job-listing__location">New York, NY</div>
      </li>
    </ul>
  </body>
</html>
"""

STARTUP_DETAIL_HTML = """
<html>
  <body>
    <div class="section--responsibilities">
      <li>Analyze datasets with SQL and Python.</li>
    </div>
    <div class="section--benefits">
      <p>Salary: $20/hr plus bonuses</p>
    </div>
    <time datetime="2025-06-01"></time>
  </body>
</html>
"""


if __name__ == "__main__":
    unittest.main()

