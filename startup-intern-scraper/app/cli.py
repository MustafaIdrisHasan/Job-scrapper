"""Command-line interface for the internship scraper."""

from __future__ import annotations

import argparse
import logging
from typing import List, Tuple

from .config import Settings, load_settings
from .models import InternshipListing
from . import nlp_infer, notify, scrapers, storage
from .scheduler import run_schedule


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    settings = load_settings()
    
    # Apply command line role filtering overrides
    if args.job_type:
        settings.job_type = args.job_type
    if args.role_category:
        settings.role_category = args.role_category
    if args.keywords:
        settings.keywords = args.keywords
    
    _configure_logging(args.debug or settings.run_debug)

    if args.command == "run":
        _run_once(settings)
    elif args.command == "schedule":
        try:
            run_schedule(lambda: _run_once(settings), settings)
        except KeyboardInterrupt:
            logging.getLogger(__name__).info("Schedule loop interrupted; exiting.")
    elif args.command == "ui":
        _launch_ui(settings)
    elif args.command == "test":
        if not _run_tests():
            return 1
    elif args.command == "help-filters":
        _show_filter_help()
    else:
        parser.print_help()
        return 1

    return 0


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="internship-scraper")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging.")
    
    # Role filtering arguments
    parser.add_argument("--job-type", choices=["internship", "fulltime", "contract", "parttime"], 
                       help="Filter by job type (internship, fulltime, contract, parttime)")
    parser.add_argument("--role-category", choices=["backend", "frontend", "fullstack", "data", "ai", "mobile", "devops", "product", "design"], 
                       help="Filter by role category (backend, frontend, fullstack, data, ai, mobile, devops, product, design)")
    parser.add_argument("--keywords", help="Custom keywords to search for (e.g., 'python react nodejs')")

    subparsers = parser.add_subparsers(dest="command")
    subparsers.add_parser("run", help="Run the scraper once.")
    subparsers.add_parser("schedule", help="Run the scraper every two days.")
    subparsers.add_parser("ui", help="Launch the optional UI.")
    subparsers.add_parser("test", help="Execute smoke tests.")
    subparsers.add_parser("help-filters", help="Show examples of role filtering options.")
    return parser


def _configure_logging(debug: bool) -> None:
    level = logging.DEBUG if debug else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        force=True,
    )


def _run_once(settings: Settings) -> Tuple[List[InternshipListing], List[InternshipListing]]:
    logger = logging.getLogger(__name__)
    logger.info("Starting internship scraper run.")
    notify.desktop_notify("Startup Internship Scraper", "Scraper running…")

    try:
        listings = scrapers.scrape_all(settings)
        deduped = _dedupe_and_infer(listings)

        state = storage.load_state(settings)
        new_listings, existing_listings = storage.split_new_and_existing(deduped, state)

        storage.export_all_outputs(deduped, settings)
        storage.save_state(
            settings, storage.update_state_with_new(state, new_listings)
        )

        notify.desktop_notify(
            "Startup Internship Scraper", f"{len(new_listings)} new internships found."
        )
        notify.email_summary(settings, new_listings)

        logger.info(
            "Scrape complete: %d listings (%d new, %d previously seen).",
            len(deduped),
            len(new_listings),
            len(existing_listings),
        )

        _print_summary(deduped, new_listings)
        return deduped, new_listings
    except Exception as exc:  # noqa: BLE001
        logger.exception("Scrape run failed: %s", exc)
        notify.desktop_notify("Startup Internship Scraper", f"Run failed: {exc}")
        raise


def _dedupe_and_infer(listings: List[InternshipListing]) -> List[InternshipListing]:
    deduped: dict[str, InternshipListing] = {}
    for listing in listings:
        listing.recommended_tech_stack = nlp_infer.infer_for_listing(listing)
        deduped[listing.id] = listing
    return list(deduped.values())


def _print_summary(
    listings: List[InternshipListing], new_listings: List[InternshipListing]
) -> None:
    logger = logging.getLogger(__name__)
    logger.info("Latest run produced %d total listings.", len(listings))
    print(f"Total listings: {len(listings)}")
    print(f"New listings: {len(new_listings)}")
    if not new_listings:
        logger.info("No new listings this run.")
        return
    logger.info("New listings:")
    for item in new_listings:
        logger.info(
            "- %s (%s) — %s",
            item.company,
            item.role_title,
            item.pay or "Pay TBD",
        )
        print(f"- {item.company} — {item.role_title} [{item.pay or 'Pay TBD'}]")


def _launch_ui(settings: Settings) -> None:
    from . import ui

    ui.launch(settings, lambda: _run_once(settings))


def _run_tests() -> bool:
    import unittest

    logger = logging.getLogger(__name__)
    logger.info("Running smoke tests...")

    suite = unittest.defaultTestLoader.discover("tests")
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    success = result.wasSuccessful()
    if success:
        logger.info("All tests passed.")
    else:
        logger.error("Tests failed.")
    return success


def _show_filter_help() -> None:
    """Show examples of how to use role filtering."""
    print("Role Filtering Examples:")
    print()
    print("Job Type Filters:")
    print("  --job-type internship     # Only internships")
    print("  --job-type fulltime       # Only full-time jobs")
    print("  --job-type contract       # Only contract work")
    print("  --job-type parttime       # Only part-time jobs")
    print()
    print("Role Category Filters:")
    print("  --role-category backend   # Backend engineering roles")
    print("  --role-category frontend  # Frontend engineering roles")
    print("  --role-category fullstack # Full-stack engineering roles")
    print("  --role-category data      # Data science/engineering roles")
    print("  --role-category ai        # AI/ML engineering roles")
    print("  --role-category mobile    # Mobile development roles")
    print("  --role-category devops    # DevOps/Infrastructure roles")
    print("  --role-category product   # Product management roles")
    print("  --role-category design    # Design/UX roles")
    print()
    print("Custom Keyword Filters:")
    print("  --keywords python,react   # Jobs containing 'python' or 'react'")
    print("  --keywords remote         # Remote-friendly jobs")
    print("  --keywords startup       # Startup companies")
    print()
    print("Example Commands:")
    print("  python -m app.cli run --job-type internship --role-category backend")
    print("  python -m app.cli run --job-type fulltime --keywords python,react,nodejs")
    print("  python -m app.cli run --role-category ai --keywords machine learning")
    print("  python -m app.cli run --job-type internship --role-category frontend --keywords react")
    print()
    print("Environment Variables (optional):")
    print("  Set JOB_TYPE, ROLE_CATEGORY, or KEYWORDS in .env file for persistent filtering")


if __name__ == "__main__":
    raise SystemExit(main())
