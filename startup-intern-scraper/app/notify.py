"""Notification utilities (desktop + email)."""

from __future__ import annotations

import logging
import smtplib
from email.message import EmailMessage
from typing import Iterable

try:
    from plyer import notification
except Exception:  # noqa: BLE001
    notification = None  # type: ignore[assignment]

from .config import Settings
from .models import InternshipListing

LOGGER = logging.getLogger(__name__)


def desktop_notify(title: str, message: str) -> None:
    """Send a desktop notification, handling platform quirks."""
    if notification is None:
        LOGGER.debug("plyer not available; skipping desktop notification.")
        return
    try:
        notification.notify(title=title, message=message, timeout=10)
    except Exception as exc:  # noqa: BLE001
        LOGGER.debug("Desktop notifications unavailable: %s", exc)


def email_summary(
    settings: Settings, new_listings: Iterable[InternshipListing]
) -> None:
    """Send a Gmail summary email for new listings."""
    items = list(new_listings)
    if not items:
        LOGGER.info("No new listings to email.")
        return

    if not (
        settings.gmail_sender
        and settings.gmail_app_password
        and settings.gmail_recipient
    ):
        LOGGER.warning("Skipping email notification; Gmail credentials missing.")
        return

    body_lines = [f"{item.company} — {item.pay or 'Pay TBD'} ({item.source.title()})" for item in items]
    body = "New internships found:\n\n" + "\n".join(body_lines)

    msg = EmailMessage()
    msg["Subject"] = "Internship Scraper Update"
    msg["From"] = settings.gmail_sender
    msg["To"] = settings.gmail_recipient
    msg.set_content(body)

    try:
        with smtplib.SMTP("smtp.gmail.com", 587) as smtp:
            smtp.starttls()
            smtp.login(settings.gmail_sender, settings.gmail_app_password)
            smtp.send_message(msg)
            LOGGER.info("Sent email update with %d listings.", len(items))
    except smtplib.SMTPAuthenticationError:
        LOGGER.error("Gmail authentication failed. Check app password settings.")
    except Exception as exc:  # noqa: BLE001
        LOGGER.error("Failed to send Gmail update: %s", exc)
