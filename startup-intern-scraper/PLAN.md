# Upgrade Plan: Salem Techsperts Laptop Scraper → CSV + Scoring

> Drop this into your repo as `PLAN.md` or a top-level docstring. Paste into Cursor/Codex and say: **"Implement this plan in the current project."**

---

## Objective

Enhance the existing scraper to:

1. Crawl **all pages** of `https://salemtechsperts.com/collections/laptops-for-sale?page=1`.
2. Extract per item: **title, price, currency, stock status, product URL, full description**.
3. Export a **CSV** `salem_laptops.csv` with the above + two heuristic scores:

   * `business_score` (daily driver: portability/battery/newer CPU).
   * `server_score` (home server: RAM/cores/storage/virtualization).
4. (Optional) Keep/change-detection & notifications you already have.

---

## Deliverables

* `scraper.py` updated with:

  * **CLI**: `--export-csv`, `--max-pages`, `--once`, `--watch`, `--interval`.
  * **Crawler**: paginated collection → product pages → description.
  * **Parsers**: robust CSS selections for title/price/status and description.
  * **CSV writer**: headers exactly:

    ```
    title,price,currency,status,url,business_score,server_score,description
    ```
  * **Console summary**: top 3 by `business_score` and top 3 by `server_score`.
* `requirements.txt` (ensure `requests`, `beautifulsoup4`).
* `README.md` section explaining usage & scoring.

---

## Tech Constraints

* Python 3.10+
* Libraries: `requests`, `beautifulsoup4`, stdlib (`csv`, `argparse`, `re`, `time`)
* Respect polite crawl (UA header, tiny sleep between requests).

---

## CLI & Usage

```bash
# CSV export (default mode we'll support)
python scraper.py --export-csv --max-pages 20

# One-off monitor run (if you already have monitoring)
python scraper.py --once

# Watch mode (if present)
python scraper.py --watch --interval 180
```

---

## Data Model

```text
Item:
  title: str
  price: float | None   # parse "$X.XX" or "From $X.XX"
  currency: "USD"
  status: "In stock" | "Sold out" | "Unknown"
  url: str
  description: str       # product page text
  business_score: float
  server_score: float
```

---

## Scoring Heuristics (simple, explainable)

* **CPU newness hint**: detect tokens like `i7-1165G7`, `i5-1235U`, `Ryzen 7/9` → map to a base score.
* **Business score** (portable/no-charger focus):

  * * keywords: `lightweight, thin, ultrabook, portable`
  * * `battery`, `long battery`, `battery life`
  * * `IPS`, `FHD`, `OLED`
  * * storage practicality `NVMe, 512GB, 1TB`
  * − gaming bricks: `gaming, RGB, 3060, 3070`
  * Normalize by `score / log(price + 10)`.
* **Server score** (home-lab focus):

  * * RAM hints `16GB, 32GB, 64GB, ECC`
  * * CPU/threads: `i7, i9, Ryzen 7/9, core, threads`
  * * storage: `NVMe, SSD, 2TB`
  * * virtualization words: `Docker, Proxmox, VM, virtualization, Hyper-V`
  * * networking: `Ethernet, 2.5G, 10G`
  * Normalize by `score / log(price + 10)`.

> Keep heuristics in a single place (e.g., `CPU_HINTS`, `keyword_score()`) for easy tuning later.

---

## Parsing Strategy

* **Collection pages**: select anchors `a[href*="/products/"]`; ascend a few parents to capture price/status text blocks.
* **Price regex**: `(?:From\s*)?\$(\d+(?:\.\d{2})?)`
* **Status detection**: `"In stock"` / `"Sold out"` in surrounding text.
* **Product page** description selectors (try in order):

  * `[itemprop="description"]`, `.product-single__description`, `.product__description`, `.product-description`, `div[id*="Description"]`; fallback to `main` text truncated to ~3k chars.

---

## Pagination Rules

* Loop `page=1..N` (`--max-pages` cap).
* If a page yields **0 items** (after page 1) or no pagination links remain, **stop** early.

---

## CSV Output

* File: `salem_laptops.csv`
* Columns (exact order):
  `title,price,currency,status,url,business_score,server_score,description`

---

## Console Output (after CSV export)

* Print a short summary:

  * "Top 3 business picks" with `title | $price | status | url (business_score=…)`
  * "Top 3 server picks" with same format.

---

## Pseudocode (high level)

```python
def crawl_collection(max_pages):
    items = {}
    for page in range(1, max_pages+1):
        soup = get_soup(COLLECTION_URL.format(page=page))
        cards = extract_card_products(soup)   # title, price, status, url
        if not cards and page > 1: break
        for c in cards: items[c["url"]] = c
        if not has_more_pages(soup): break
        sleep(0.6)
    for url, it in items.items():
        it["description"] = fetch_description(url)
        sleep(0.5)
    return list(items.values())

def export_csv(items):
    attach_scores(items)  # fills business_score, server_score
    write_csv(items, "salem_laptops.csv")
    print_top3(items, kind="business_score")
    print_top3(items, kind="server_score")
```

---

## Acceptance Criteria

* Running `python scraper.py --export-csv --max-pages 20`:

  * Produces `salem_laptops.csv` with **≥ 10 rows** (assuming site has listings).
  * Each row has **non-empty title, url, description**; price may be `None` if absent.
  * Console prints **Top 3** lists for both categories with scores.
* Code is idempotent, handles missing fields gracefully, and avoids duplicate items.

---

## Optional (If You Already Have Monitoring)

* Keep your change-detection cache.
* On change, desktop toast & Discord webhook summary (env `DISCORD_WEBHOOK_URL`).
* **Do not** block the CSV export path; they should be independent code paths.

---

## README Snippet (to add)

````md
### CSV Export
```bash
python scraper.py --export-csv --max-pages 20
````

Outputs `salem_laptops.csv` with descriptions and two scores:

* `business_score`: portability/battery/newer CPU
* `server_score`: RAM/cores/storage/virtualization

Upload the CSV to ChatGPT for a personalized shortlist (business daily driver + home server pick).

```

---

**Implement now:** Update `scraper.py`, add scoring helpers, robust selectors, CSV writer, and README notes per this plan.
