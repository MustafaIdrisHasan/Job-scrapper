"""Persistence helpers for internship listings."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable, List, Tuple

import pandas as pd

from .config import Settings
from .exporter import export_csv, export_excel, export_pdf
from .models import InternshipListing


@dataclass
class ScraperState:
    known_ids: set[str]
    last_run: datetime | None = None

    def to_json(self) -> dict:
        return {
            "known_ids": sorted(self.known_ids),
            "last_run": self.last_run.isoformat() if self.last_run else None,
        }

    @classmethod
    def from_json(cls, payload: dict) -> "ScraperState":
        known = set(payload.get("known_ids", []))
        last_run_raw = payload.get("last_run")
        last_run = datetime.fromisoformat(last_run_raw) if last_run_raw else None
        return cls(known_ids=known, last_run=last_run)


def state_path(settings: Settings) -> Path:
    return settings.output_dir / "state.json"


def load_state(settings: Settings) -> ScraperState:
    path = state_path(settings)
    if not path.exists():
        return ScraperState(known_ids=set(), last_run=None)
    data = json.loads(path.read_text(encoding="utf-8"))
    return ScraperState.from_json(data)


def save_state(settings: Settings, state: ScraperState) -> None:
    path = state_path(settings)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state.to_json(), indent=2), encoding="utf-8")


def split_new_and_existing(
    listings: Iterable[InternshipListing], state: ScraperState
) -> Tuple[List[InternshipListing], List[InternshipListing]]:
    new_items: List[InternshipListing] = []
    existing_items: List[InternshipListing] = []
    for listing in listings:
        if listing.id in state.known_ids:
            existing_items.append(listing)
        else:
            new_items.append(listing)
    return new_items, existing_items


def update_state_with_new(
    state: ScraperState, new_listings: Iterable[InternshipListing]
) -> ScraperState:
    for listing in new_listings:
        state.known_ids.add(listing.id)
    state.last_run = datetime.utcnow()
    return state


def export_all_outputs(
    listings: List[InternshipListing], settings: Settings
) -> None:
    """Write CSV, Excel, and PDF artifacts to disk."""
    if not listings:
        df = pd.DataFrame(columns=_columns())
    else:
        df = pd.DataFrame([_listing_to_row(item) for item in listings])

    settings.output_dir.mkdir(parents=True, exist_ok=True)
    csv_path = settings.output_dir / "internships.csv"
    excel_path = settings.output_dir / "internships.xlsx"
    pdf_path = settings.output_dir / "internships_report.pdf"

    export_csv(df, csv_path)
    export_excel(df, excel_path)
    # export_pdf(df, pdf_path)  # Temporarily disabled due to formatting issues


def _columns() -> List[str]:
    return [
        "id",
        "source",
        "company",
        "role_title",
        "location",
        "pay",
        "posted_at",
        "responsibilities",
        "recommended_tech_stack",
        "source_url",
        "scraped_at",
    ]


def _listing_to_row(listing: InternshipListing) -> dict:
    return {
        "id": listing.id,
        "source": listing.source,
        "company": listing.company,
        "role_title": listing.role_title,
        "location": listing.location,
        "pay": listing.pay,
        "posted_at": listing.posted_at,
        "responsibilities": listing.responsibilities,
        "recommended_tech_stack": ", ".join(listing.recommended_tech_stack),
        "source_url": listing.source_url,
        "scraped_at": listing.scraped_at.isoformat(),
    }
