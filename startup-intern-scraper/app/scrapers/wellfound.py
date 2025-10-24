"""Optional Wellfound scraper."""

from __future__ import annotations

import logging
import re
from typing import List, Optional, TYPE_CHECKING
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from ..config import Settings
from ..models import InternshipListing

if TYPE_CHECKING:
    from . import HttpClient

LOGGER = logging.getLogger(__name__)
BASE_URL = "https://wellfound.com"
START_URL = "https://wellfound.com/role/l/internship"


def scrape(settings: Settings, client: HttpClient) -> List[InternshipListing]:
    """Collect Wellfound internship listings if enabled."""
    try:
        response = client.get(START_URL, headers={
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Accept-Language": "en-US,en;q=0.5",
            "Accept-Encoding": "gzip, deflate",
            "Connection": "keep-alive",
        })
    except Exception as exc:  # noqa: BLE001
        LOGGER.warning("Unable to access Wellfound: %s", exc)
        return []

    if not _page_has_static_content(response.text):
        LOGGER.warning(
            "Wellfound page requires dynamic rendering; skipping (see TODO in README)."
        )
        return []

    soup = BeautifulSoup(response.text, "lxml")
    # Try multiple selectors for job cards
    cards = soup.select("div[data-test='job-card']")
    if not cards:
        cards = soup.select("div.job-card")
    if not cards:
        cards = soup.select("div[class*='job']")
    
    listings: List[InternshipListing] = []
    for card in cards:
        listing = _parse_card(card)
        if listing:
            listings.append(listing)
    return listings


def _page_has_static_content(html: str) -> bool:
    # Check for various job card indicators
    job_indicators = [
        "data-test=\"job-card\"",
        "class=\"job-card\"",
        "data-testid=\"job-card\"",
        "jobTitle",
        "companyName"
    ]
    return any(indicator in html for indicator in job_indicators)


def _parse_card(card) -> Optional[InternshipListing]:
    # Try multiple selectors for each field
    title_el = (card.select_one("[data-test='job-title']") or 
                card.select_one(".job-title") or 
                card.select_one("h3") or 
                card.select_one("h2"))
    
    company_el = (card.select_one("[data-test='company-name']") or 
                  card.select_one(".company-name") or 
                  card.select_one(".company") or
                  card.select_one("span[class*='company']"))
    
    link_el = card.select_one("a[href]")
    
    if not (title_el and company_el and link_el):
        return None
        
    title = title_el.get_text(strip=True)
    company = company_el.get_text(strip=True)
    href = link_el.get("href")
    url = urljoin(BASE_URL, href)

    location_el = (card.select_one("[data-test='job-location']") or 
                   card.select_one(".location") or
                   card.select_one("span[class*='location']"))
    
    pay_el = (card.select_one("[data-test='salary-range']") or 
              card.select_one(".salary") or
              card.select_one("span[class*='salary']"))
    
    description_el = (card.select_one("[data-test='job-description']") or 
                      card.select_one(".description") or
                      card.select_one("p"))

    listing = InternshipListing(
        source="wellfound",
        company=company,
        role_title=title,
        source_url=url,
        responsibilities=description_el.get_text(" ", strip=True) if description_el else "",
        location=location_el.get_text(strip=True) if location_el else None,
        pay=pay_el.get_text(strip=True) if pay_el else None,
    )
    return listing
