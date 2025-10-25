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
    
    # Focus only on internships page for remote internships
    urls.append("https://www.workatastartup.com/internships")
    
    # Also include general jobs page if not specifically filtering for internships
    if not settings.job_type or settings.job_type != "internship":
        urls.append("https://www.workatastartup.com/jobs")
    
    return urls


def scrape(settings: Settings, client: HttpClient) -> List[InternshipListing]:
    """Collect YC internship listings."""
    listings: List[InternshipListing] = []
    seen: set[str] = set()
    
    # Get URLs based on filters
    list_urls = _get_urls_for_filters(settings)

    for list_url in list_urls:
        try:
            response = client.get(list_url)
        except Exception as exc:  # noqa: BLE001
            LOGGER.warning("Failed to load YC listing page %s: %s", list_url, exc)
            continue
            
        # Try to extract from JSON data first (for dynamic content)
        json_listings = _extract_from_json_data(response.text)
        if json_listings:
            for job_data in json_listings:
                listing = _parse_json_job(job_data)
                if not listing:
                    continue
                if listing.id in seen:
                    continue
                
                # Apply filters
                if settings.job_type == "internship" and not _is_internship_role(listing):
                    continue
                
                if settings.keywords and not _matches_keywords(listing, settings.keywords):
                    continue
                
                seen.add(listing.id)
                listings.append(listing)
        else:
            # Fallback to HTML parsing
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
                
                # Apply filters
                if settings.job_type == "internship" and not _is_internship_role(listing):
                    continue
                
                if settings.keywords and not _matches_keywords(listing, settings.keywords):
                    continue
                
                seen.add(listing.id)
                listings.append(listing)

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
    
    # Enhanced pay extraction - look in multiple places
    pay_el = (card.select_one(".role-card__salary") or 
              card.select_one("[data-testid='salary']") or
              card.select_one(".salary") or
              card.select_one("span:contains('$')") or
              card.select_one("span:contains('USD')") or
              card.select_one("span:contains('hour')") or
              card.select_one("span:contains('stipend')"))
    
    posted_el = card.select_one("time")

    responsibilities = _fetch_responsibilities(client, source_url)
    
    # Try to extract pay from the detail page if not found in card
    if not pay_el and source_url:
        pay_from_detail = _extract_pay_from_detail(client, source_url)
        if pay_from_detail:
            pay_el = type('obj', (object,), {'get_text': lambda x, strip=True: pay_from_detail})()

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


def _is_internship_role(listing: InternshipListing) -> bool:
    """Check if a role is an internship based on title and description."""
    title_lower = listing.role_title.lower()
    desc_lower = listing.responsibilities.lower()
    
    internship_keywords = [
        "intern", "internship", "co-op", "coop", "student", "trainee", 
        "summer intern", "winter intern", "part-time intern", "remote intern"
    ]
    
    return any(keyword in title_lower or keyword in desc_lower for keyword in internship_keywords)


def _is_remote_job(listing: InternshipListing) -> bool:
    """Check if a job is remote-friendly."""
    location_lower = (listing.location or "").lower()
    desc_lower = listing.responsibilities.lower()
    
    remote_keywords = [
        "remote", "work from home", "wfh", "distributed", "virtual",
        "anywhere", "global", "worldwide", "flexible location", "us / remote",
        "remote (us)", "united states (remote)", "san francisco - remote"
    ]
    
    # Also check if location contains remote indicators
    remote_location_indicators = [
        "remote", "us / remote", "remote (us)", "united states (remote)",
        "san francisco - remote", "remote / remote"
    ]
    
    return (any(keyword in location_lower or keyword in desc_lower for keyword in remote_keywords) or
            any(indicator in location_lower for indicator in remote_location_indicators))


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


def _extract_from_json_data(html_content: str) -> List[dict]:
    """Extract job data from JSON embedded in HTML."""
    import re
    import json
    
    # Look for JSON data in script tags
    json_pattern = r'window\.__INITIAL_STATE__\s*=\s*({.*?});'
    match = re.search(json_pattern, html_content, re.DOTALL)
    
    if not match:
        # Try alternative patterns
        json_pattern = r'"jobs":\s*(\[.*?\])'
        match = re.search(json_pattern, html_content, re.DOTALL)
    
    if match:
        try:
            data = json.loads(match.group(1))
            if isinstance(data, dict) and 'jobs' in data:
                return data['jobs']
            elif isinstance(data, list):
                return data
        except json.JSONDecodeError:
            pass
    
    return []


def _parse_json_job(job_data: dict) -> Optional[InternshipListing]:
    """Parse job data from JSON."""
    try:
        title = job_data.get('title', '')
        company = job_data.get('companyName', '')
        location = job_data.get('location', '')
        pay = job_data.get('salaryRange', '')
        job_url = job_data.get('url', '')
        job_type = job_data.get('type', '')
        role_type = job_data.get('roleSpecificType', '')
        
        # Build full URL
        if job_url and not job_url.startswith('http'):
            source_url = urljoin(BASE_URL, job_url)
        else:
            source_url = job_url
            
        # Extract skills/tech stack
        skills = job_data.get('skills', [])
        tech_stack = ', '.join(skills) if skills else ''
        
        # Get description from job data if available
        description = job_data.get('description', '')
        
        listing = InternshipListing(
            source="yc",
            company=company,
            role_title=title,
            source_url=source_url,
            responsibilities=description,
            location=location,
            pay=pay,
            recommended_tech_stack=tech_stack,
            posted_at=job_data.get('createdAt', ''),
        )
        
        return listing
        
    except Exception as exc:  # noqa: BLE001
        LOGGER.debug("Failed to parse JSON job data: %s", exc)
        return None


def _extract_pay_from_detail(client: HttpClient, detail_url: str) -> str:
    """Extract pay information from job detail page."""
    try:
        response = client.get(detail_url)
    except Exception as exc:  # noqa: BLE001
        LOGGER.debug("Failed to load YC detail page for pay %s: %s", detail_url, exc)
        return ""

    soup = BeautifulSoup(response.text, "lxml")

    # Look for pay information in various places
    pay_selectors = [
        "span:contains('$')",
        "span:contains('USD')",
        "span:contains('hour')",
        "span:contains('stipend')",
        "span:contains('salary')",
        "div:contains('$')",
        "p:contains('$')",
        "[data-testid='salary']",
        ".salary",
        ".pay"
    ]

    for selector in pay_selectors:
        elements = soup.select(selector)
        for element in elements:
            text = element.get_text(strip=True)
            if any(keyword in text.lower() for keyword in ['$', 'usd', 'hour', 'stipend', 'salary', 'pay']):
                return text

    return ""
