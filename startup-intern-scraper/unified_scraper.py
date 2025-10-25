#!/usr/bin/env python3
"""
Unified Scraper System
Choose between Salem Techsperts laptop scraper and Y Combinator job scraper
"""

import argparse
import csv
import re
import time
import sys
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime
import requests
from bs4 import BeautifulSoup
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

@dataclass
class LaptopItem:
    """Data model for laptop items from Salem Techsperts"""
    title: str
    price: Optional[float]
    currency: str = "USD"
    status: str = "Unknown"
    url: str = ""
    description: str = ""
    business_score: float = 0.0
    server_score: float = 0.0

@dataclass
class JobItem:
    """Data model for job items from Y Combinator"""
    company: str
    role_title: str
    location: str
    pay: Optional[str]
    source_url: str
    responsibilities: str = ""
    recommended_tech_stack: str = ""

class UnifiedScraper:
    """Unified scraper for both Salem Techsperts and Y Combinator"""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
    
    def scrape_salem_laptops(self, max_pages: int = 20) -> List[LaptopItem]:
        """Scrape Salem Techsperts laptops with scoring"""
        logger.info(f"Scraping Salem Techsperts laptops (max {max_pages} pages)")
        
        items = {}
        base_url = "https://salemtechsperts.com/collections/laptops-for-sale"
        
        for page in range(1, max_pages + 1):
            url = f"{base_url}?page={page}"
            logger.info(f"Scraping page {page}: {url}")
            
            try:
                response = self.session.get(url)
                response.raise_for_status()
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Extract product cards
                cards = self._extract_laptop_cards(soup)
                if not cards and page > 1:
                    logger.info("No more items found, stopping pagination")
                    break
                
                for card in cards:
                    if card['url'] not in items:
                        items[card['url']] = card
                
                # Check if there are more pages
                if not self._has_next_page(soup):
                    logger.info("No next page found, stopping pagination")
                    break
                
                time.sleep(0.6)  # Polite crawling
                
            except Exception as e:
                logger.error(f"Error scraping page {page}: {e}")
                break
        
        # Fetch descriptions for each item
        logger.info(f"Fetching descriptions for {len(items)} items")
        for url, item in items.items():
            try:
                item['description'] = self._fetch_laptop_description(url)
                time.sleep(0.5)  # Polite crawling
            except Exception as e:
                logger.error(f"Error fetching description for {url}: {e}")
                item['description'] = ""
        
        # Convert to LaptopItem objects and calculate scores
        laptop_items = []
        for item_data in items.values():
            laptop = LaptopItem(
                title=item_data.get('title', ''),
                price=item_data.get('price'),
                currency=item_data.get('currency', 'USD'),
                status=item_data.get('status', 'Unknown'),
                url=item_data.get('url', ''),
                description=item_data.get('description', '')
            )
            self._calculate_scores(laptop)
            laptop_items.append(laptop)
        
        return laptop_items
    
    def scrape_yc_jobs(self, job_type: str = "internship", role_category: str = None, keywords: str = None) -> List[JobItem]:
        """Scrape Y Combinator jobs"""
        logger.info(f"Scraping Y Combinator jobs (type: {job_type}, category: {role_category})")
        
        # Import the existing YC scraper
        sys.path.append('.')
        from app.scrapers.yc import scrape as yc_scrape
        from app.config import Settings
        from app.scrapers import HttpClient
        
        # Create settings with filters
        settings = Settings()
        settings.job_type = job_type
        settings.role_category = role_category
        settings.keywords = keywords
        
        client = HttpClient(settings)
        listings = yc_scrape(settings, client)
        
        # Convert to JobItem objects
        job_items = []
        for listing in listings:
            job = JobItem(
                company=listing.company,
                role_title=listing.role_title,
                location=listing.location or "",
                pay=listing.pay,
                source_url=listing.source_url,
                responsibilities=listing.responsibilities,
                recommended_tech_stack=listing.recommended_tech_stack or ""
            )
            job_items.append(job)
        
        return job_items
    
    def _extract_laptop_cards(self, soup: BeautifulSoup) -> List[Dict]:
        """Extract laptop cards from collection page"""
        cards = []
        
        # Try multiple selectors for product cards
        product_selectors = [
            'a[href*="/products/"]',
            '.product-item',
            '.product-card',
            '.grid-product'
        ]
        
        for selector in product_selectors:
            elements = soup.select(selector)
            if elements:
                logger.info(f"Found {len(elements)} items with selector: {selector}")
                break
        
        for element in elements:
            try:
                # Extract URL
                url = element.get('href', '')
                if not url.startswith('http'):
                    url = f"https://salemtechsperts.com{url}"
                
                # Extract title
                title_selectors = ['h3', 'h4', '.product-title', '.product-name', 'a']
                title = ""
                for sel in title_selectors:
                    title_elem = element.select_one(sel)
                    if title_elem:
                        title = title_elem.get_text(strip=True)
                        break
                
                # Extract price
                price = self._extract_price(element)
                
                # Extract status
                status = self._extract_status(element)
                
                if title and url:
                    cards.append({
                        'title': title,
                        'price': price,
                        'currency': 'USD',
                        'status': status,
                        'url': url
                    })
                    
            except Exception as e:
                logger.error(f"Error extracting card: {e}")
                continue
        
        return cards
    
    def _extract_price(self, element) -> Optional[float]:
        """Extract price from element"""
        text = element.get_text()
        price_pattern = r'(?:From\s*)?\$(\d+(?:\.\d{2})?)'
        match = re.search(price_pattern, text)
        if match:
            return float(match.group(1))
        return None
    
    def _extract_status(self, element) -> str:
        """Extract stock status from element"""
        text = element.get_text().lower()
        if 'sold out' in text or 'out of stock' in text:
            return 'Sold out'
        elif 'in stock' in text or 'available' in text:
            return 'In stock'
        return 'Unknown'
    
    def _has_next_page(self, soup: BeautifulSoup) -> bool:
        """Check if there's a next page"""
        next_selectors = [
            'a[rel="next"]',
            '.pagination .next',
            '.pagination-next',
            'a:contains("Next")'
        ]
        
        for selector in next_selectors:
            if soup.select_one(selector):
                return True
        return False
    
    def _fetch_laptop_description(self, url: str) -> str:
        """Fetch product description from product page"""
        try:
            response = self.session.get(url)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Try multiple selectors for description
            desc_selectors = [
                '[itemprop="description"]',
                '.product-single__description',
                '.product__description',
                '.product-description',
                'div[id*="Description"]',
                '.product-details',
                '.product-info'
            ]
            
            for selector in desc_selectors:
                desc_elem = soup.select_one(selector)
                if desc_elem:
                    return desc_elem.get_text(strip=True)[:3000]  # Truncate to 3k chars
            
            # Fallback to main content
            main = soup.select_one('main')
            if main:
                return main.get_text(strip=True)[:3000]
                
        except Exception as e:
            logger.error(f"Error fetching description from {url}: {e}")
        
        return ""
    
    def _calculate_scores(self, laptop: LaptopItem):
        """Calculate business and server scores for laptop"""
        text = f"{laptop.title} {laptop.description}".lower()
        
        # CPU hints
        cpu_scores = {
            'i9': 10, 'i7': 8, 'i5': 6, 'i3': 4,
            'ryzen 9': 10, 'ryzen 7': 8, 'ryzen 5': 6, 'ryzen 3': 4,
            'm1': 9, 'm2': 10, 'm3': 11
        }
        
        cpu_score = 0
        for cpu, score in cpu_scores.items():
            if cpu in text:
                cpu_score = max(cpu_score, score)
        
        # Business score (portability/battery focus)
        business_keywords = {
            'lightweight': 3, 'thin': 2, 'ultrabook': 4, 'portable': 2,
            'battery': 2, 'long battery': 3, 'battery life': 2,
            'ips': 1, 'fhd': 1, 'oled': 2,
            'nvme': 2, '512gb': 1, '1tb': 2
        }
        
        business_penalties = {
            'gaming': -3, 'rgb': -2, '3060': -2, '3070': -2, '3080': -2
        }
        
        business_score = cpu_score
        for keyword, score in business_keywords.items():
            if keyword in text:
                business_score += score
        
        for keyword, penalty in business_penalties.items():
            if keyword in text:
                business_score += penalty
        
        # Server score (RAM/cores/storage focus)
        server_keywords = {
            '16gb': 3, '32gb': 5, '64gb': 7, 'ecc': 2,
            'core': 1, 'threads': 1, 'thread': 1,
            'nvme': 2, 'ssd': 1, '2tb': 3,
            'docker': 2, 'proxmox': 3, 'vm': 2, 'virtualization': 2,
            'ethernet': 1, '2.5g': 2, '10g': 3
        }
        
        server_score = cpu_score
        for keyword, score in server_keywords.items():
            if keyword in text:
                server_score += score
        
        # Normalize by price
        price_factor = laptop.price or 1000
        laptop.business_score = business_score / (1 + 0.1 * (price_factor / 100))
        laptop.server_score = server_score / (1 + 0.1 * (price_factor / 100))
    
    def export_laptops_csv(self, items: List[LaptopItem], filename: str = None):
        """Export laptops to CSV with timestamp"""
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"salem_laptops_{timestamp}.csv"
        
        with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(['title', 'price', 'currency', 'status', 'url', 'business_score', 'server_score', 'description'])
            
            for item in items:
                writer.writerow([
                    item.title,
                    item.price,
                    item.currency,
                    item.status,
                    item.url,
                    f"{item.business_score:.2f}",
                    f"{item.server_score:.2f}",
                    item.description
                ])
        
        logger.info(f"Exported {len(items)} laptops to {filename}")
        return filename
    
    def export_jobs_csv(self, items: List[JobItem], filename: str = None):
        """Export jobs to CSV with timestamp"""
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"yc_jobs_{timestamp}.csv"
        
        with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(['company', 'role_title', 'location', 'pay', 'source_url', 'responsibilities', 'recommended_tech_stack'])
            
            for item in items:
                writer.writerow([
                    item.company,
                    item.role_title,
                    item.location,
                    item.pay,
                    item.source_url,
                    item.responsibilities,
                    item.recommended_tech_stack
                ])
        
        logger.info(f"Exported {len(items)} jobs to {filename}")
        return filename
    
    def print_top_picks(self, items: List[LaptopItem]):
        """Print top 3 business and server picks"""
        if not items:
            logger.info("No items to display")
            return
        
        # Top 3 business picks
        business_sorted = sorted(items, key=lambda x: x.business_score, reverse=True)[:3]
        print("\nTop 3 Business Picks (Daily Driver):")
        for i, item in enumerate(business_sorted, 1):
            price_str = f"${item.price}" if item.price else "Price N/A"
            print(f"{i}. {item.title} | {price_str} | {item.status} | {item.url} (business_score={item.business_score:.2f})")
        
        # Top 3 server picks
        server_sorted = sorted(items, key=lambda x: x.server_score, reverse=True)[:3]
        print("\nTop 3 Server Picks (Home Lab):")
        for i, item in enumerate(server_sorted, 1):
            price_str = f"${item.price}" if item.price else "Price N/A"
            print(f"{i}. {item.title} | {price_str} | {item.status} | {item.url} (server_score={item.server_score:.2f})")

def main():
    parser = argparse.ArgumentParser(description='Unified Scraper System')
    parser.add_argument('--scraper', choices=['salem', 'yc'], required=True,
                       help='Choose scraper: salem (laptops) or yc (jobs)')
    
    # Salem laptop options
    parser.add_argument('--export-csv', action='store_true',
                       help='Export to CSV (Salem laptops)')
    parser.add_argument('--max-pages', type=int, default=20,
                       help='Maximum pages to scrape (Salem laptops)')
    
    # YC job options
    parser.add_argument('--job-type', choices=['internship', 'fulltime', 'contract', 'parttime'],
                       help='Filter by job type (YC jobs)')
    parser.add_argument('--role-category', choices=['backend', 'frontend', 'fullstack', 'data', 'ai', 'mobile', 'devops', 'product', 'design'],
                       help='Filter by role category (YC jobs)')
    parser.add_argument('--keywords', help='Custom keywords to search for (YC jobs)')
    
    args = parser.parse_args()
    
    scraper = UnifiedScraper()
    
    if args.scraper == 'salem':
        logger.info("Starting Salem Techsperts laptop scraper")
        items = scraper.scrape_salem_laptops(max_pages=args.max_pages)
        
        if args.export_csv:
            filename = scraper.export_laptops_csv(items)
            print(f"\nLaptop data exported to: {filename}")
            scraper.print_top_picks(items)
        else:
            logger.info(f"Found {len(items)} laptops")
            for item in items[:5]:  # Show first 5
                print(f"- {item.title} | ${item.price} | {item.status}")
    
    elif args.scraper == 'yc':
        logger.info("Starting Y Combinator job scraper")
        items = scraper.scrape_yc_jobs(
            job_type=args.job_type,
            role_category=args.role_category,
            keywords=args.keywords
        )
        
        filename = scraper.export_jobs_csv(items)
        print(f"\nJob data exported to: {filename}")
        logger.info(f"Found {len(items)} jobs")
        for item in items[:5]:  # Show first 5
            print(f"- {item.company}: {item.role_title} | {item.location} | {item.pay}")

if __name__ == "__main__":
    main()
