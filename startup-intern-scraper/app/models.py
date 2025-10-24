"""Data models for internship listings and scraper state."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional


def _make_hash(*parts: str) -> str:
    digest = hashlib.sha256()
    for part in parts:
        digest.update(part.encode("utf-8", "ignore"))
        digest.update(b"\0")
    return digest.hexdigest()


@dataclass(slots=True)
class InternshipListing:
    source: str
    company: str
    role_title: str
    source_url: str
    responsibilities: str = ""
    pay: Optional[str] = None
    location: Optional[str] = None
    posted_at: Optional[str] = None  # ISO string for simplicity
    recommended_tech_stack: List[str] = field(default_factory=list)
    scraped_at: datetime = field(default_factory=lambda: datetime.utcnow())
    tags: List[str] = field(default_factory=list)
    id: str = field(init=False)

    def __post_init__(self) -> None:
        self.id = _make_hash(self.source, self.company, self.role_title, self.source_url)


@dataclass(slots=True)
class ScrapeResult:
    listings: List[InternshipListing]
    new_listings: List[InternshipListing]
    existing_listings: List[InternshipListing]

