# Startup Internship Scraper

Lightweight, terminal-first scraper that gathers internship listings from Y Combinator's Work at a Startup board and startup.jobs, infers recommended tech stacks, exports CSV/XLSX/PDF reports, and notifies you via desktop alerts and Gmail.

## Requirements
- Python 3.10+
- (Recommended) Virtual environment

## Setup
```bash
# Windows (PowerShell)
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# macOS / Linux
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

## Environment Configuration
Copy `.env.sample` to `.env` and update the values:

```
cp .env.sample .env  # macOS / Linux
copy .env.sample .env  # Windows
```

Required keys:
- `GMAIL_SENDER`: Gmail address that will send summary messages.
- `GMAIL_APP_PASSWORD`: Gmail App Password (create at https://myaccount.google.com > Security > App Passwords).
- `GMAIL_RECIPIENT`: Address to receive updates (can match `GMAIL_SENDER`).

Optional:
- `SCRAPE_DELAY_MIN_SECONDS` / `SCRAPE_DELAY_MAX_SECONDS`: polite delay window between requests.
- `USER_AGENT`: Custom user-agent string.
- `ENABLE_WELLFOUND`: Set to `true` to attempt optional Wellfound scraping (skips gracefully if HTML is obfuscated).
- `RATE_LIMITS`: Comma-separated `domain=seconds` pairs (e.g., `workatastartup.com=10,startup.jobs=15`).

## Usage
Run all commands from the `startup-intern-scraper` directory.

```bash
# One-off scrape
python -m app.cli run

# Continuous schedule (default: immediately, then every 2 days)
python -m app.cli schedule

# Optional Tkinter UI with "Run Now" button
python -m app.cli ui

# Smoke tests (HTML fixture based)
python -m app.cli test
```

Outputs are written to `out/`:
- `internships.csv`
- `internships.xlsx`
- `internships_report.pdf`
- `state.json` (internal deduplication state)

## Scheduling Alternatives
- **Windows Task Scheduler:** Create a basic task that runs `python -m app.cli run` every 2 days. Ensure the task starts in the project folder and uses your Python interpreter.
- **macOS / Linux cron:** `0 9 */2 * * /path/to/python -m app.cli run >> /path/to/log 2>&1`

## Notifications
- Desktop notifications use `plyer`. On macOS, grant terminal notification access if prompted. On Linux, ensure `notify-send` (libnotify) is installed.
- Gmail summary emails include `Company — Pay (Source)` for new listings since the previous run. Authentication errors are logged without stopping the run.

## Troubleshooting
- **Site blocking / captchas:** Increase delay values or update `RATE_LIMITS`. Runs are intentionally infrequent (every 2 days) to stay polite.
- **Gmail auth failures:** Regenerate the App Password and confirm two-factor authentication is enabled for the sender account.
- **Windows notifications missing:** Verify Focus Assist is disabled and allow notifications for the Python/terminal app in Settings.
- **Missing dependencies:** Re-run `pip install -r requirements.txt`. For PDF export issues on Apple Silicon macOS, ensure `libjpeg` and `zlib` are available or switch to `reportlab`.

## Project Structure
```
app/
  cli.py            # CLI entry points
  config.py         # .env parsing and settings
  exporter.py       # CSV/XLSX/PDF writers
  models.py         # Dataclasses for records
  nlp_infer.py      # Tech stack inference
  notify.py         # Desktop + Gmail notifications
  scheduler.py      # 2-day loop using schedule
  storage.py        # Persistence and state
  ui.py             # Optional Tkinter UI
  scrapers/
    yc.py           # Work at a Startup parser
    startup_jobs.py # startup.jobs parser
    wellfound.py    # Optional stub (HTML only)
docs/
  IMPLEMENTATION_PLAN.md
tests/
  test_nlp.py
  test_scrapers.py
out/                # Generated artifacts (ignored until created)
```

## License
MIT License – see `LICENSE` for details.

