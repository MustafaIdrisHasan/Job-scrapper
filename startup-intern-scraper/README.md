# Unified Scraper System

A unified scraper system that lets you choose between Salem Techsperts laptop scraper and Y Combinator job scraper.

## Features

### 🖥️ Salem Techsperts Laptop Scraper
- Crawls all pages of laptop listings
- Extracts title, price, currency, stock status, product URL, full description
- Calculates business_score (portability/battery/newer CPU) and server_score (RAM/cores/storage/virtualization)
- Exports to CSV with scoring

### 💼 Y Combinator Job Scraper  
- Scrapes Y Combinator Work at a Startup jobs
- Filters by job type, role category, and keywords
- Extracts company, role, location, pay, responsibilities, tech stack
- Exports to CSV

## Installation

```bash
pip install requests beautifulsoup4
```

## Usage

### Salem Techsperts Laptop Scraper

```bash
# Basic scraping with CSV export
python unified_scraper.py --scraper salem --export-csv --max-pages 20

# Just scrape without CSV export
python unified_scraper.py --scraper salem --max-pages 10
```

**Output**: `salem_laptops_YYYYMMDD_HHMMSS.csv` with columns:
- `title,price,currency,status,url,business_score,server_score,description`

**Scoring**:
- `business_score`: portability/battery/newer CPU (higher = better for daily driver)
- `server_score`: RAM/cores/storage/virtualization (higher = better for home server)

### Y Combinator Job Scraper

```bash
# Scrape all jobs
python unified_scraper.py --scraper yc

# Filter by job type
python unified_scraper.py --scraper yc --job-type internship

# Filter by role category
python unified_scraper.py --scraper yc --role-category backend

# Filter by keywords
python unified_scraper.py --scraper yc --keywords python,react

# Combined filters
python unified_scraper.py --scraper yc --job-type internship --role-category backend --keywords python
```

**Output**: `yc_jobs_YYYYMMDD_HHMMSS.csv` with columns:
- `company,role_title,location,pay,source_url,responsibilities,recommended_tech_stack`

## Examples

### Find Remote Internships
```bash
python unified_scraper.py --scraper yc --job-type internship --keywords remote
```

### Find Business Laptops
```bash
python unified_scraper.py --scraper salem --export-csv --max-pages 20
# Then check the CSV for high business_score items
```

### Find Server Laptops
```bash
python unified_scraper.py --scraper salem --export-csv --max-pages 20
# Then check the CSV for high server_score items
```

## Scoring Heuristics

### Business Score (Daily Driver)
**Positive factors**:
- Keywords: `lightweight, thin, ultrabook, portable`
- Battery: `battery, long battery, battery life`
- Display: `IPS, FHD, OLED`
- Storage: `NVMe, 512GB, 1TB`
- CPU: `i7, i9, Ryzen 7/9, M1/M2/M3`

**Negative factors**:
- Gaming: `gaming, RGB, 3060, 3070, 3080`

### Server Score (Home Lab)
**Positive factors**:
- RAM: `16GB, 32GB, 64GB, ECC`
- CPU: `i7, i9, Ryzen 7/9, core, threads`
- Storage: `NVMe, SSD, 2TB`
- Virtualization: `Docker, Proxmox, VM, virtualization, Hyper-V`
- Networking: `Ethernet, 2.5G, 10G`

## Output Files

- `salem_laptops_YYYYMMDD_HHMMSS.csv` - Laptop listings with scores (timestamped)
- `yc_jobs_YYYYMMDD_HHMMSS.csv` - Job listings with details (timestamped)

## Tips

1. **For laptop shopping**: Use the business_score to find portable daily drivers
2. **For home servers**: Use the server_score to find powerful lab machines  
3. **For job hunting**: Filter by role category and keywords to find relevant positions
4. **Upload CSV to ChatGPT**: Get personalized recommendations based on your needs

## Troubleshooting

- **Permission errors**: Close any Excel files that might be open
- **No results**: Try increasing `--max-pages` or check if the website is accessible
- **Slow scraping**: The scraper includes polite delays to avoid overwhelming servers