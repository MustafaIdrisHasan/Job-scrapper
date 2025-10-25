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
    posted_at: str = ""
    scraped_at: str = ""

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
        """Scrape Y Combinator jobs - focus on internships"""
        logger.info(f"Scraping Y Combinator jobs (type: {job_type}, category: {role_category})")
        
        # Try to use existing data first (more reliable)
        try:
            import pandas as pd
            df = pd.read_csv('out/internships.csv')
            logger.info(f"Found {len(df)} existing listings")
            
            # If no data, skip to live scraping
            if len(df) == 0:
                logger.info("No existing data found, skipping to live scraping")
                raise Exception("No existing data")
            
            # Filter for internships if requested
            if job_type == "internship":
                filtered_df = df[df['role_title'].str.contains('intern|Intern', case=False, na=False)]
                logger.info(f"Filtered to {len(filtered_df)} internship roles")
            else:
                filtered_df = df
            
            # Apply additional filters
            if role_category:
                # Map role categories to keywords - search in multiple fields
                role_keywords = {
                    "backend": "backend|server|api|database|engineer|software|development",
                    "frontend": "frontend|ui|ux|react|angular|vue|design",
                    "fullstack": "fullstack|full-stack|full stack|engineer",
                    "data": "data|analytics|ml|ai|machine learning|research|scientist",
                    "ai": "ai|artificial intelligence|ml|machine learning|research|engineer|scientist",
                    "mobile": "mobile|ios|android|react native|app",
                    "devops": "devops|infrastructure|cloud|aws|azure|ops",
                    "product": "product|pm|product manager|management",
                    "design": "design|ui|ux|designer|visual"
                }
                if role_category in role_keywords:
                    pattern = role_keywords[role_category]
                    # Search in role_title, responsibilities, and recommended_tech_stack
                    filtered_df = filtered_df[
                        filtered_df['role_title'].fillna('').str.contains(pattern, case=False, na=False) |
                        filtered_df['responsibilities'].fillna('').str.contains(pattern, case=False, na=False) |
                        filtered_df['recommended_tech_stack'].fillna('').str.contains(pattern, case=False, na=False)
                    ]
                    logger.info(f"After role filter: {len(filtered_df)} listings")
            
            if keywords:
                keyword_list = [kw.strip().lower() for kw in keywords.split(",")]
                for keyword in keyword_list:
                    # Handle NaN values in string columns
                    filtered_df = filtered_df[
                        filtered_df['role_title'].fillna('').str.contains(keyword, case=False, na=False) |
                        filtered_df['company'].fillna('').str.contains(keyword, case=False, na=False) |
                        filtered_df['responsibilities'].fillna('').str.contains(keyword, case=False, na=False)
                    ]
                logger.info(f"After keyword filter: {len(filtered_df)} listings")
            
            # Convert to JobItem objects
            job_items = []
            for _, row in filtered_df.iterrows():
                job = JobItem(
                    company=row['company'],
                    role_title=row['role_title'],
                    location=row['location'] or "",
                    pay=row['pay'],
                    source_url=row['source_url'],
                    responsibilities=row['responsibilities'],
                    recommended_tech_stack=row['recommended_tech_stack'] or "",
                    posted_at=row.get('posted_at', ''),
                    scraped_at=row.get('scraped_at', '')
                )
                job_items.append(job)
            
            return job_items
            
        except Exception as e:
            logger.error(f"Error using existing data: {e}")
            logger.info("Falling back to live scraping...")
            
            # Fallback to live scraping with JSON extraction
            try:
                logger.info("Attempting live scraping from YC website...")
                response = self.session.get("https://www.workatastartup.com/internships", 
                                           headers={
                                               'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                                               'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                                               'Accept-Language': 'en-US,en;q=0.5',
                                               'Accept-Encoding': 'gzip, deflate',
                                               'Connection': 'keep-alive',
                                               'Upgrade-Insecure-Requests': '1',
                                           }, timeout=10)
                response.raise_for_status()
                
                # Extract JSON data from the page
                import re
                import json
                
                # Look for JSON data in the HTML - try multiple patterns
                patterns = [
                    r'"jobs":\s*(\[.*?\])',
                    r'jobs":\s*(\[.*?\])',
                    r'"jobs":\s*(\[.*?\]),',
                    r'window\.__INITIAL_STATE__\s*=\s*({.*?});',
                    r'__INITIAL_STATE__\s*=\s*({.*?});'
                ]
                
                jobs_data = None
                for pattern in patterns:
                    match = re.search(pattern, response.text, re.DOTALL)
                    if match:
                        try:
                            data = json.loads(match.group(1))
                            if isinstance(data, dict) and 'jobs' in data:
                                jobs_data = data['jobs']
                            elif isinstance(data, list):
                                jobs_data = data
                            if jobs_data:
                                break
                        except json.JSONDecodeError:
                            continue
                
                # If no JSON found, try to extract from URL-encoded data
                has_id = '"id":' in response.text
                has_title = '"title":' in response.text
                logger.info(f"Checking for JSON structure: 'id' in text: {has_id}, 'title' in text: {has_title}")
                logger.info(f"Response content length: {len(response.text)}")
                logger.info(f"Contains 'internship': {'internship' in response.text.lower()}")
                logger.info(f"Contains 'Machine Learning': {'Machine Learning' in response.text}")
                
                # Try to find the data even if it's URL-encoded
                if not jobs_data and ('internship' in response.text.lower() or 'Machine Learning' in response.text):
                    logger.info("Found internship content, attempting to extract data...")
                    # Look for the data in the response
                    if 'Machine Learning' in response.text:
                        start = response.text.find('Machine Learning')
                        logger.info(f"Found 'Machine Learning' at position {start}")
                        
                        # Look backwards for the start of the array - try multiple patterns
                        json_start = None
                        for i in range(start, max(0, start-2000), -1):
                            if response.text[i:i+2] == '[{':
                                json_start = i
                                logger.info(f"Found array start at position {json_start}")
                                break
                        
                        if json_start is None:
                            # Try to find the actual array start by looking for the pattern we saw
                            for i in range(start, max(0, start-2000), -1):
                                if response.text[i:i+10] == '&quot;},{&quot;':
                                    json_start = i + 10  # Start after the pattern
                                    logger.info(f"Found array start after pattern at position {json_start}")
                                    break
                        
                        if json_start is None:
                            # Fallback: look for any opening brace
                            for i in range(start, max(0, start-1000), -1):
                                if response.text[i] == '{':
                                    json_start = i
                                    logger.info(f"Found object start at position {json_start}")
                                    break
                            else:
                                json_start = start - 100
                        
                        # Look forward for the end
                        end = response.text.find('}]', start)
                        if end > start:
                            json_text = response.text[json_start:end+2]
                            logger.info(f"Extracted JSON block: {len(json_text)} characters")
                            
                            # Show first 200 characters for debugging
                            logger.info(f"First 200 chars: {json_text[:200]}")
                            
                            # Try to find the actual array start within the extracted text
                            array_start = json_text.find('[{')
                            if array_start > 0:
                                json_text = json_text[array_start:]
                                logger.info(f"Found array start within text, new length: {len(json_text)}")
                            else:
                                # If we don't have an array, we need to create one from the objects
                                if json_text.startswith('{'):
                                    # Find all the individual objects and wrap them in an array
                                    objects = []
                                    current_pos = 0
                                    brace_count = 0
                                    start_pos = 0
                                    
                                    for i, char in enumerate(json_text):
                                        if char == '{':
                                            if brace_count == 0:
                                                start_pos = i
                                            brace_count += 1
                                        elif char == '}':
                                            brace_count -= 1
                                            if brace_count == 0:
                                                # Found a complete object
                                                obj_text = json_text[start_pos:i+1]
                                                objects.append(obj_text)
                                    
                                    if objects:
                                        json_text = '[' + ','.join(objects) + ']'
                                        logger.info(f"Created array from {len(objects)} objects, new length: {len(json_text)}")
                            
                            # Clean up HTML entities first
                            import html
                            cleaned_text = html.unescape(json_text)
                            logger.info(f"Cleaned HTML entities, new length: {len(cleaned_text)}")
                            
                            # Try to parse the cleaned JSON
                            try:
                                jobs_data = json.loads(cleaned_text)
                                logger.info(f"Successfully parsed {len(jobs_data)} items from cleaned JSON")
                            except json.JSONDecodeError as e:
                                logger.error(f"Cleaned JSON parse error: {e}")
                                # Try URL decoding
                                import urllib.parse
                                decoded_text = urllib.parse.unquote(cleaned_text)
                                try:
                                    jobs_data = json.loads(decoded_text)
                                    logger.info(f"Successfully parsed {len(jobs_data)} items from decoded JSON")
                                except json.JSONDecodeError as e2:
                                    logger.error(f"Decoded JSON parse error: {e2}")
                                    # Try without URL decoding
                                    try:
                                        jobs_data = json.loads(json_text)
                                        logger.info(f"Successfully parsed {len(jobs_data)} items from raw JSON")
                                    except json.JSONDecodeError as e3:
                                        logger.error(f"Raw JSON parse error: {e3}")
                                        pass
                        else:
                            logger.info("Could not find array end")
                
                if not jobs_data and '"id":' in response.text and '"title":' in response.text:
                    logger.info("Found JSON structure with id and title, attempting extraction...")
                    # Look for the start of the array
                    start = response.text.find('"id":')
                    if start > 0:
                        # Look backwards for the start of the array
                        for i in range(start, max(0, start-2000), -1):
                            if response.text[i:i+2] == '[{':
                                json_start = i
                                break
                        else:
                            json_start = start - 100
                            
                        # Look forward for the end
                        end = response.text.find('}]', start)
                        if end > start:
                            json_text = response.text[json_start:end+2]
                            logger.info(f"Extracted JSON block: {len(json_text)} characters")
                            
                            # Try URL decoding first
                            import urllib.parse
                            decoded_text = urllib.parse.unquote(json_text)
                            try:
                                jobs_data = json.loads(decoded_text)
                                logger.info(f"Successfully parsed {len(jobs_data)} items from decoded JSON")
                            except json.JSONDecodeError as e:
                                logger.error(f"Decoded JSON parse error: {e}")
                                # Try without URL decoding
                                try:
                                    jobs_data = json.loads(json_text)
                                    logger.info(f"Successfully parsed {len(jobs_data)} items from raw JSON")
                                except json.JSONDecodeError as e2:
                                    logger.error(f"Raw JSON parse error: {e2}")
                                    pass
                
                if jobs_data:
                    logger.info(f"Found {len(jobs_data)} jobs in JSON data")
                    
                    job_items = []
                    for job_data in jobs_data:
                            # Apply filters
                            if job_type == "internship" and job_data.get('type', '').lower() != 'internship':
                                continue
                                
                            if role_category:
                                title_lower = (job_data.get('title') or '').lower()
                                role_lower = (job_data.get('roleSpecificType') or '').lower()
                                if role_category == "ai" and not any(kw in title_lower or kw in role_lower for kw in ['ai', 'machine learning', 'ml', 'artificial intelligence']):
                                    continue
                                elif role_category == "backend" and not any(kw in title_lower or kw in role_lower for kw in ['backend', 'server', 'api', 'database', 'engineer']):
                                    continue
                            
                            if keywords:
                                keyword_list = [kw.strip().lower() for kw in keywords.split(",")]
                                search_text = f"{job_data.get('title', '')} {job_data.get('companyName', '')}".lower()
                                if not any(keyword in search_text for keyword in keyword_list):
                                    continue
                            
                            # Create JobItem
                            job = JobItem(
                                company=job_data.get('companyName', ''),
                                role_title=job_data.get('title', ''),
                                location=job_data.get('location', ''),
                                pay=job_data.get('salaryRange', ''),
                                source_url=f"https://www.workatastartup.com{job_data.get('url', '')}",
                                responsibilities='',  # Would need to fetch from detail page
                                recommended_tech_stack=', '.join(job_data.get('skills', [])),
                                posted_at=job_data.get('createdAt', ''),
                                scraped_at=datetime.now().isoformat()
                            )
                            job_items.append(job)
                        
                    logger.info(f"Successfully scraped {len(job_items)} jobs")
                    return job_items
                else:
                    logger.warning("No JSON data found in page")
                    return []
                
            except Exception as e2:
                logger.error(f"Live scraping also failed: {e2}")
                return []
    
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
                
                # Extract title - try multiple approaches
                title = ""
                
                # Method 1: Look for title in the element itself
                title_selectors = ['h3', 'h4', '.product-title', '.product-name', 'a']
                for sel in title_selectors:
                    title_elem = element.select_one(sel)
                    if title_elem:
                        title = title_elem.get_text(strip=True)
                        if title:
                            break
                
                # Method 2: If no title found, use the link text
                if not title:
                    title = element.get_text(strip=True)
                
                # Method 3: Extract from URL if still no title
                if not title and url:
                    # Extract product name from URL
                    url_parts = url.split('/')
                    if 'products' in url_parts:
                        product_name = url_parts[-1].replace('-', ' ').title()
                        title = product_name
                
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
        
        # Try multiple price patterns
        price_patterns = [
            r'(?:From\s*)?\$(\d+(?:\.\d{2})?)',  # $123.45
            r'\$(\d+)',  # $123
            r'(\d+(?:\.\d{2})?)\s*USD',  # 123.45 USD
            r'Price:\s*\$(\d+(?:\.\d{2})?)',  # Price: $123.45
        ]
        
        for pattern in price_patterns:
            match = re.search(pattern, text)
            if match:
                try:
                    return float(match.group(1))
                except ValueError:
                    continue
        
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
            writer.writerow(['company', 'role_title', 'location', 'pay', 'source_url', 'responsibilities', 'recommended_tech_stack', 'posted_at', 'scraped_at'])
            
            for item in items:
                writer.writerow([
                    item.company,
                    item.role_title,
                    item.location,
                    item.pay,
                    item.source_url,
                    item.responsibilities,
                    item.recommended_tech_stack,
                    item.posted_at,
                    item.scraped_at
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
        
        # Show jobs with date information
        print(f"\nJob Listings ({len(items)} found):")
        for i, item in enumerate(items[:10], 1):  # Show first 10
            posted_info = f"Posted: {item.posted_at}" if item.posted_at else "Posted: Unknown"
            scraped_info = f"Scraped: {item.scraped_at}" if item.scraped_at else "Scraped: Unknown"
            print(f"{i}. {item.company}: {item.role_title}")
            print(f"   Location: {item.location} | Pay: {item.pay}")
            print(f"   {posted_info} | {scraped_info}")
            print(f"   URL: {item.source_url}")
            print()

if __name__ == "__main__":
    main()
