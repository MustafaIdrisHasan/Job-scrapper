"""Scraper for Indeed.com internships."""

from __future__ import annotations

import logging
from typing import List, Optional, TYPE_CHECKING
from urllib.parse import urljoin, quote

from bs4 import BeautifulSoup

from ..config import Settings
from ..models import InternshipListing

if TYPE_CHECKING:
    from . import HttpClient

LOGGER = logging.getLogger(__name__)
BASE_URL = "https://www.indeed.com"

def _build_search_url(settings: Settings) -> str:
    """Build Indeed search URL based on filters."""
    query_parts = []
    
    # Base query
    if settings.job_type == "internship":
        query_parts.append("internship")
    elif settings.job_type == "fulltime":
        query_parts.append("full time")
    elif settings.job_type == "contract":
        query_parts.append("contract")
    elif settings.job_type == "parttime":
        query_parts.append("part time")
    else:
        query_parts.append("internship")  # Default to internships
    
    # Add role category keywords
    if settings.role_category:
        role_keywords = {
            "backend": "backend engineer",
            "frontend": "frontend engineer", 
            "fullstack": "full stack engineer",
            "data": "data scientist data engineer",
            "ai": "machine learning AI engineer",
            "mobile": "mobile developer iOS Android",
            "devops": "devops engineer",
            "product": "product manager",
            "design": "UX UI designer"
        }
        if settings.role_category in role_keywords:
            query_parts.append(role_keywords[settings.role_category])
    
    # Add custom keywords
    if settings.keywords:
        query_parts.append(settings.keywords)
    
    query = " ".join(query_parts)
    return f"https://www.indeed.com/jobs?q={query}&l=remote&sort=date"


def scrape(settings: Settings, client: HttpClient) -> List[InternshipListing]:
    listings: List[InternshipListing] = []
    visited: set[str] = set()
    next_url = _build_search_url(settings)

    for _ in range(5):  # Limit to 5 pages to avoid being blocked
        try:
            response = client.get(next_url, headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.5",
                "Accept-Encoding": "gzip, deflate",
                "Connection": "keep-alive",
                "Upgrade-Insecure-Requests": "1",
            })
        except Exception as exc:  # noqa: BLE001
            LOGGER.warning("Failed to load Indeed page %s: %s", next_url, exc)
            break

        soup = BeautifulSoup(response.text, "lxml")
        cards = soup.select("div[data-jk]")
        if not cards:
            cards = soup.select("div.job_seen_beacon")

        for card in cards:
            listing = _parse_card(card, client)
            if not listing:
                continue
            if listing.id in visited:
                continue
            
            # Apply keyword filtering if specified
            if settings.keywords and not _matches_keywords(listing, settings.keywords):
                continue
            
            visited.add(listing.id)
            listings.append(listing)

        # Look for next page link
        next_link = soup.select_one("a[aria-label='Next Page']")
        if next_link and next_link.get("href"):
            next_url = urljoin(BASE_URL, next_link["href"])
        else:
            break

    return listings


def _parse_card(card, client: HttpClient) -> Optional[InternshipListing]:
    title_el = card.select_one("h2.jobTitle a") or card.select_one("a[data-jk]")
    company_el = card.select_one("span[data-testid='company-name']") or card.select_one(".companyName")
    link_el = card.select_one("h2.jobTitle a") or card.select_one("a[data-jk]")

    if not (title_el and company_el and link_el):
        return None

    title = title_el.get_text(strip=True)
    company = company_el.get_text(strip=True)
    href = link_el.get("href")
    source_url = urljoin(BASE_URL, href)
    location_el = card.select_one("div[data-testid='job-location']") or card.select_one(".companyLocation")

    responsibilities, pay, posted_at = _fetch_details(client, source_url)

    listing = InternshipListing(
        source="indeed",
        company=company,
        role_title=title,
        source_url=source_url,
        responsibilities=responsibilities,
        pay=pay,
        location=location_el.get_text(strip=True) if location_el else None,
        posted_at=posted_at,
    )
    return listing


def _fetch_details(
    client: HttpClient, url: str
) -> tuple[str, Optional[str], Optional[str]]:
    try:
        response = client.get(url, headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        })
    except Exception as exc:  # noqa: BLE001
        LOGGER.debug("Failed to load Indeed detail %s: %s", url, exc)
        return ("", None, None)

    soup = BeautifulSoup(response.text, "lxml")
    desc_section = soup.select_one("div#jobDescriptionText") or soup.select_one("div.jobsearch-jobDescriptionText")
    pay_section = soup.select_one("span[data-testid='attribute_snippet_testid']")
    posted_el = soup.select_one("span[data-testid='myJobsStateDate']")

    responsibilities = ""
    if desc_section:
        responsibilities = desc_section.get_text(" ", strip=True)
    
    pay_text = None
    if pay_section:
        pay_text = pay_section.get_text(strip=True)

    posted_at = None
    if posted_el:
        posted_at = posted_el.get_text(strip=True)

    return (responsibilities, pay_text, posted_at)


def _matches_keywords(listing: InternshipListing, keywords: str) -> bool:
    """Check if a listing matches the specified keywords."""
    if not keywords:
        return True
    
    keyword_list = [kw.strip().lower() for kw in keywords.split(",")]
    search_text = f"{listing.role_title} {listing.company} {listing.responsibilities}".lower()
    
    return any(keyword in search_text for keyword in keyword_list)
