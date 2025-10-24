"""Scraper for Y Combinator Work at a Startup internships."""

from __future__ import annotations

import logging
from typing import Iterable, List, Optional, TYPE_CHECKING
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from ..config import Settings
from ..models import InternshipListing

if TYPE_CHECKING:
    from . import HttpClient
LOGGER = logging.getLogger(__name__)
BASE_URL = "https://www.workatastartup.com"

def _get_urls_for_filters(settings: Settings) -> list[str]:
    """Generate URLs based on job type and role category filters."""
    urls = []
    
    if settings.job_type == "internship":
        urls.append("https://www.workatastartup.com/internships")
    elif settings.job_type == "fulltime":
        urls.append("https://www.workatastartup.com/jobs")
    else:
        # Default: get both internships and jobs
        urls.extend([
            "https://www.workatastartup.com/internships",
            "https://www.workatastartup.com/jobs"
        ])
    
    # For now, we'll rely on keyword filtering rather than URL-based filtering
    # since YC's URL structure may not support direct role filtering
    
    return urls


def scrape(settings: Settings, client: HttpClient) -> List[InternshipListing]:
    """Collect YC internship listings."""
    listings: List[InternshipListing] = []
    seen: set[str] = set()
    
    # Get URLs based on filters
    list_urls = _get_urls_for_filters(settings)

    for list_url in list_urls:
        next_url = list_url
        for _ in range(5):  # hard stop to avoid infinite loops
            try:
                response = client.get(next_url)
            except Exception as exc:  # noqa: BLE001
                LOGGER.warning("Failed to load YC listing page %s: %s", next_url, exc)
                break
            soup = BeautifulSoup(response.text, "lxml")
            # Try new structure first
            cards = soup.select("div.w-full.bg-beige-lighter")
            if not cards:
                # Fallback to old structure
                cards = soup.select("div.role-card")
                if not cards:
                    cards = soup.select("article[class*='role']")
            for card in cards:
                listing = _parse_card(card, client)
                if not listing:
                    continue
                if listing.id in seen:
                    continue
                
                # Apply keyword filtering if specified
                if settings.keywords and not _matches_keywords(listing, settings.keywords):
                    continue
                
                seen.add(listing.id)
                listings.append(listing)

            next_link = soup.select_one("a[rel='next']")
            if next_link and next_link.get("href"):
                next_url = urljoin(BASE_URL, next_link["href"])
            else:
                break

    return listings


def _parse_card(card, client: HttpClient) -> Optional[InternshipListing]:
    # Try new structure first
    title_el = card.select_one("a[data-jobid]") or card.select_one(".job-name a")
    company_el = card.select_one("a[target='company'] span.font-bold") or card.select_one(".company-details span.font-bold")
    link_el = card.select_one("a[data-jobid]") or card.select_one("a[href*='/jobs/']")
    
    # Fallback to old structure
    if not title_el:
        title_el = card.select_one(".role-card__title") or card.select_one("h3")
    if not company_el:
        company_el = card.select_one(".role-card__company") or card.select_one("h4")
    if not link_el:
        link_el = card.select_one("a[href]")

    if not (title_el and company_el and link_el):
        return None

    title = title_el.get_text(strip=True)
    company = company_el.get_text(strip=True)
    relative_url = link_el.get("href")
    source_url = urljoin(BASE_URL, relative_url)

    # Try new structure for location and pay
    location_el = card.select_one(".job-details span:contains('Remote')") or card.select_one(".job-details span:contains('CA')") or card.select_one(".job-details span:contains('US')")
    if not location_el:
        location_el = card.select_one(".role-card__location")
    
    pay_el = card.select_one(".role-card__salary")
    posted_el = card.select_one("time")

    responsibilities = _fetch_responsibilities(client, source_url)

    listing = InternshipListing(
        source="yc",
        company=company,
        role_title=title,
        source_url=source_url,
        responsibilities=responsibilities,
        location=location_el.get_text(strip=True) if location_el else None,
        pay=pay_el.get_text(strip=True) if pay_el else None,
        posted_at=posted_el.get("datetime") if posted_el else None,
    )

    return listing


def _matches_keywords(listing: InternshipListing, keywords: str) -> bool:
    """Check if a listing matches the specified keywords."""
    if not keywords:
        return True
    
    keyword_list = [kw.strip().lower() for kw in keywords.split(",")]
    search_text = f"{listing.role_title} {listing.company} {listing.responsibilities}".lower()
    
    return any(keyword in search_text for keyword in keyword_list)


def _fetch_responsibilities(client: HttpClient, detail_url: str) -> str:
    try:
        response = client.get(detail_url)
    except Exception as exc:  # noqa: BLE001
        LOGGER.debug("Failed to load YC detail page %s: %s", detail_url, exc)
        return ""
    soup = BeautifulSoup(response.text, "lxml")
    section = (
        soup.select_one("section#job-description")
        or soup.select_one("div[data-testid='job-description']")
    )
    if not section:
        return ""
    paragraphs = [p.get_text(" ", strip=True) for p in section.find_all(["p", "li"])]
    cleaned = " ".join(paragraphs)
    return cleaned.strip()
