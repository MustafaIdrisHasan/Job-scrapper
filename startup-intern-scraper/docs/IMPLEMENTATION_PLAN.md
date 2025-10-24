# Startup Internship Scraper – Implementation Plan

## 1. Target Sites & Extraction Strategy
- **Y Combinator – Work at a Startup internships**  
  - **Entry URL:** `https://www.workatastartup.com/roles?jobType=internship&remote=false` plus remote variant.  
  - **Listing selector:** `div.role-card` (backup: `article[class*="role"]`). Within each card capture company (`.role-card__company`), title (`.role-card__title`), location (`.role-card__location`). Pay occasionally in `.role-card__salary`.  
  - **Detail fetch:** Follow `a.role-card__link` to get responsibilities from `section#job-description` (fallback: `div[data-testid="job-description"]`).  
  - **Pagination:** Inspect `button[aria-label="Next"]`; loop until disabled.  
  - **Fallback:** If layout shifts, look for JSON LD script (`type="application/ld+json"`) containing job data.

- **Startup Jobs (startup.jobs) internships**  
  - **Entry URL:** `https://startup.jobs/internship-jobs`.  
  - **Listing selector:** `ul.jobs-list > li` (backup: `div.job-listing` within `#jobs-list`). Extract company (`.job-listing__company`), title (`.job-listing__title`), location (`.job-listing__location`).  
  - **Detail fetch:** Follow `a.job-listing__link` → responsibilities in `div.section--description`, bullets in `div.section--responsibilities`. Pay often under `.section--benefits`.  
  - **Pagination:** Use `a.pagination__item--next`. Continue until absent.  
  - **Fallback:** If markup shifts, parse embedded `window.__INITIAL_STATE__` JSON via regex.

- **Wellfound (optional, flag-controlled)**  
  - **Entry URL:** `https://wellfound.com/role/l/internship` (requires query parameters).  
  - **Feasibility check:** Attempt HTML GET; if response lacks listing markers (`data-test="job-card"` or script tags with `apolloState`), log warning and skip.  
  - **Behavior:** Code behind `ENABLE_WELLFOUND` flag. If HTML is accessible, parse cards from `div[data-test="job-card"]` retrieving company (`.styles__companyName`), title, location, pay, description. Otherwise return empty with `TODO` note in logs and CLI.

## 2. Anti-Scraping & Politeness
- Send headers per request: `User-Agent` (configurable), `Accept-Language`, `Referer` pointing to the site root.
- Wrap requests in domain-aware session with retries (`requests.adapters.HTTPAdapter` + `Retry` for 429/5xx).  
- Randomized delay between requests: uniform `[SCRAPE_DELAY_MIN_SECONDS, SCRAPE_DELAY_MAX_SECONDS]` sourced from config; per domain override map in config for future tuning.
- Respect robots.txt note: read once per domain (manual awareness – only scrape publicly listed internship pages with no login requirement).
- Exponential backoff (2, 4, 8s) on HTTP errors up to 3 attempts; log and skip gracefully on final failure.

## 3. Data Model & Storage Flow
- **Primary record – `InternshipListing`:**  
  | Field | Type | Example |
  | --- | --- | --- |
  | `id` | `str` (hash) | `yc-figma-product-intern` |
  | `source` | `Literal["yc","startup_jobs","wellfound"]` | `yc` |
  | `company` | `str` | `Figma` |
  | `role_title` | `str` | `Product Engineering Intern` |
  | `location` | `str | None` | `San Francisco, CA (Hybrid)` |
  | `responsibilities` | `str` (clean paragraph) | `Work with backend team to build APIs...` |
  | `pay` | `str | None` | `$38/hr` |
  | `source_url` | `str` | `https://www.workatastartup.com/jobs/12345` |
  | `posted_at` | `date | None` | `2025-05-21` |
  | `recommended_tech_stack` | `list[str]` (3-7 items) | `["Python", "REST APIs", "AWS Basics", "Postgres"]` |
  | `tags` | `list[str]` (optional categories) | `["backend", "internship"]` |
  | `scraped_at` | `datetime` | `2025-10-24T13:00:00Z` |

- **State tracking:** `out/state.json` persists known listing IDs and last run timestamp.  
- **Outputs:** always rewrite `out/internships.csv`, `out/internships.xlsx`, `out/internships_report.pdf`. Maintain atomic write via temp file rename.
- **Modules Diagram:**
  ```
  cli.py ─┬─ config.py (load env + defaults)
          ├─ scheduler.py (schedule loop -> cli.run_once)
          ├─ ui.py (optional buttons -> cli.run_once)
          └─ run_once() ──> scrapers/… producing InternshipListing
                               ↓
                            nlp_infer.py (tech stack)
                               ↓
                            storage.py (dedupe + state)
                               ↓
                            exporter.py (CSV/XLSX/PDF)
                               ↓
                            notify.py (desktop + email)
  ```

## 4. NLP / Tech Stack Inference
- Maintain keyword sets grouped by category: `LANGS`, `WEB`, `CLOUD`, `DATA`, `MOBILE`, `ML`, `DEVOPS`, `SECURITY`, `PRODUCT_TOOLS`.  
- Parse responsibilities + role title + pay text -> tokenize to lowercase words/bigrams. Use simple weighted counts (prefer longest matches).  
- Select top items across categories ensuring diversity; cap duplicates.  
- If no direct hits, map role title to fallback template (e.g., roles containing `backend` -> `["Python", "REST APIs", "Postgres", "Docker"]`).  
- Append domain-informed items (e.g., if company URL contains `.ai` add `Machine Learning Foundations`).  
- Return list of 3–7 unique skills.

## 5. Notifications & Scheduling
- **Desktop Notifications (plyer):**  
  - On run start: `title="Startup Internship Scraper"`, `message="Scraper running…"`.  
  - On completion: report count of new listings.  
  - Guard with try/except to avoid crash if not supported.
- **Email Summary (smtplib + Gmail SMTP):**  
  - Use TLS on `smtp.gmail.com:587`.  
  - Subject: `Internship Scraper Update`.  
  - Plaintext body listing `Company — Pay (Source)`.  
  - On auth failure log error without raising.
- **Scheduling:**  
  - `python -m app.cli schedule` uses `schedule.every(2).days.at("09:00")` with configurable hour; default run immediately on start then every 2 days.  
  - Provide alternative instructions in README: Windows Task Scheduler XML snippet; macOS/Linux cron entry `0 9 */2 * *`.
- **On-demand flow:** `cli run` to execute once; `cli ui` optional Tkinter window hooking into same run function.

## 6. Configuration Strategy
- `.env` loaded via `python-dotenv`.  
- Keys include Gmail creds, delays, user-agent, optional toggles (`ENABLE_WELLFOUND`).  
- Provide `.env.sample` with placeholders.  
- Use `config.py` to parse env, apply defaults, cast to proper types (floats, bool).  
- Sensitive values never logged; only indicate missing configuration.

## 7. Logging, Error Handling, Tests
- Configure `logging` with module-level logger; default level INFO, CLI `--debug` flag sets DEBUG.  
- Each scraper catches request parsing errors, logs warning with listing URL, continues.  
- Rate limit or HTTP errors escalate to warning; fatal errors raise custom `ScraperError`.
- Tests (under `tests/` or within CLI `test` command):
  - `test_scrapers_smoke`: fetch first page for each enabled scraper, assert ≥1 parsed listing. Mock responses in offline mode by storing HTML snippets (future TODO).  
  - `test_inference`: sample text -> expected keywords subset.  
  - CLI `python -m app.cli test` runs these using `unittest`.

## 8. CLI & Execution Commands
- **Environment setup:**  
  - Windows: `python -m venv .venv` → `.\.venv\Scripts\Activate.ps1`.  
  - macOS/Linux: `python3 -m venv .venv` → `source .venv/bin/activate`.  
  - Install deps: `pip install -r requirements.txt`.
- **Run once:** `python -m app.cli run`.  
- **Schedule loop:** `python -m app.cli schedule`.  
- **Optional UI:** `python -m app.cli ui`.  
- **Tests:** `python -m app.cli test`.  
- **Notes:**  
  - macOS notifications may need `osascript` entitlement; fallback to console message.  
  - Windows notifications require running in a context with Action Center enabled; advise enabling app notifications if missing.  
  - On Linux, plyer backend may require `notify-send` (libnotify); document alternative.

## 9. File Layout Checklist
- `/app` package with modules specified in requirements, plus `scrapers` subpackage.  
- `/out` directory created at runtime (ensure exists).  
- `README.md`, `requirements.txt`, `.env.sample`, `LICENSE`.  
- `docs/IMPLEMENTATION_PLAN.md` maintained as source-of-truth plan.

This plan satisfies Phase 0 requirements. Next steps: scaffold package, implement scrapers/NLP/storage/exporters/notifications, wire CLI, produce outputs, and run final summary.

