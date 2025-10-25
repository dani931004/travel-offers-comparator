#!/usr/bin/env python3
"""
Teztour.bg scraper using Playwright for JavaScript-rendered content.
Scrapes travel offers from https://www.teztour.bg/
"""

import re
import asyncio
from dataclasses import dataclass, asdict
from datetime import datetime
from typing import List, Dict, Any, Optional
from bs4 import BeautifulSoup
from playwright_scraper_base import PlaywrightScraperBase, BaseOffer, run_scraper


@dataclass
class TeztourOffer(BaseOffer):
    """Data structure for Teztour.bg travel offers"""
    pass


class TeztourScraper(PlaywrightScraperBase):
    """Scraper for Teztour.bg using Playwright"""
    
    def __init__(
        self,
        base_url: str,
        output_file: str,
        debug: bool = False,
        no_enrich: bool = False,
        batch_size: int = 50,
        pw_concurrency: int = 5,
        dot_mmdd: bool = False,
        **kwargs,
    ):
        # Accept extra kwargs to be compatible with run_scraper's signature
        super().__init__(base_url, output_file, debug)
        self.no_enrich = no_enrich
        self.batch_size = batch_size
        self.pw_concurrency = pw_concurrency
        self.dot_mmdd = dot_mmdd
        
    def parse_price(self, price_text: str) -> str:
        """Extract numeric price from text"""
        if not price_text:
            return ""
        
        # Remove whitespace and extract numbers
        price_text = price_text.strip()
        
        # Try to find price with currency (EUR, BGN, лв, etc.)
        patterns = [
            r'(\d+\.?\d*)\s*€',
            r'(\d+\.?\d*)\s*EUR',
            r'(\d+\.?\d*)\s*(BGN|лв\.?)',
            r'(\d+\.?\d*)\s*лв',
            r'(\d+\.?\d*)',  # Just numbers as fallback
        ]
        
        for pattern in patterns:
            match = re.search(pattern, price_text, re.IGNORECASE)
            if match:
                price = match.group(1)
                # Check if we captured currency
                if len(match.groups()) > 1 and match.group(2):
                    currency = match.group(2)
                else:
                    # Try to detect currency from original text
                    if '€' in price_text or 'EUR' in price_text.upper():
                        currency = '€'
                    else:
                        currency = 'лв.'
                return f"{price} {currency}"
        
        return price_text
    
    def parse_dates(self, date_text: str) -> str:
        """Extract date range from text"""
        if not date_text:
            return ""
        
        date_text = date_text.strip()
        
        # Look for date patterns like "01.11" or "01.11.2025"
        dates = re.findall(r'\d{1,2}\.\d{1,2}\.?\d{0,4}', date_text)
        
        if len(dates) >= 2:
            return f"{dates[0]} - {dates[1]}"
        elif len(dates) == 1:
            return dates[0]
        
        # Try to extract from text like "за 7 нощувки" 
        nights_match = re.search(r'за\s+(\d+)\s*нощувки?', date_text, re.IGNORECASE)
        if nights_match:
            return f"{nights_match.group(1)} нощувки"
        
        return date_text
    
    def extract_destination(self, title: str, text_content: str = "") -> str:
        """Extract destination from title or description"""
        combined_text = f"{title} {text_content}".lower()
        
        # Common destinations
        destinations = {
            'египет': 'Египет', 'egypt': 'Египет',
            'турция': 'Турция', 'turkey': 'Турция',
            'гърция': 'Гърция', 'greece': 'Гърция',
            'дубай': 'Дубай', 'dubai': 'Дубай',
            'малдиви': 'Малдиви', 'maldives': 'Малдиви',
            'тайланд': 'Тайланд', 'thailand': 'Тайланд',
            'испания': 'Испания', 'spain': 'Испания',
            'италия': 'Италия', 'italy': 'Италия',
            'португалия': 'Португалия', 'portugal': 'Португалия',
            'франция': 'Франция', 'france': 'Франция',
            'кипър': 'Кипър', 'cyprus': 'Кипър',
            'черна гора': 'Черна гора', 'montenegro': 'Черна гора',
            'хърватия': 'Хърватия', 'croatia': 'Хърватия',
            'мароко': 'Мароко', 'morocco': 'Мароко',
            'тунис': 'Тунис', 'tunisia': 'Тунис',
            'занзибар': 'Занзибар', 'zanzibar': 'Занзибар',
            'анталия': 'Турция', 'antalya': 'Турция',
            'бодрум': 'Турция', 'bodrum': 'Турция',
            'белек': 'Турция', 'belek': 'Турция',
        }
        
        for key, value in destinations.items():
            if key in combined_text:
                return value
        
        return "Unknown"
    
    async def discover_destinations(self) -> List[Dict[str, str]]:
        """Discover all destination pages from the website navigation"""
        # The country slugs return 404 or redirect heavily; fallback to main page scraping
        if self.debug:
            print("Skipping destination discovery; will scrape main page instead.")
        return []
    
    async def scrape_destination(self, destination: Dict[str, str]) -> List[TeztourOffer]:
        """Scrape all offers from a specific destination page"""
        if self.debug:
            print(f"\nScraping destination: {destination['name']}")
        
        try:
            # Fetch destination page
            html_content = await self.fetch_page(
                destination['url'],
                wait_for_selector='body',
                timeout=30000
            )
            
            if not html_content:
                return []
            
            # Scroll to load more content
            await self.scroll_to_bottom(scroll_pause_time=1.0, max_scrolls=3)
            
            # Try clicking load more button
            try:
                await self.click_load_more('button:has-text("ПОКАЖИ ОЩЕ")', max_clicks=2, wait_time=1.5)
            except:
                pass
            
            # Get updated content
            html_content = await self.page.content()
            
            # Extract offers with known destination
            offers = await self.extract_offers_from_page(html_content, destination['name'])
            
            if self.debug:
                print(f"  Found {len(offers)} offers for {destination['name']}")
            
            return offers
            
        except Exception as e:
            if self.debug:
                print(f"  Error scraping {destination['name']}: {e}")
            return []
    
    async def extract_offers_from_page(self, html_content: str, destination_name: str = "Unknown") -> List[TeztourOffer]:
        """Extract offers from HTML content"""
        soup = BeautifulSoup(html_content, 'html.parser')
        offers = []
        
        # Try multiple possible selectors for offer cards
        selectors_to_try = [
            'div.hotel-card',
            'div.offer-card',
            'div.hotel-item',
            'div.tour-card',
            'article.hotel',
            'div[class*="hotel"]',
            'div[class*="offer"]',
            'div[class*="tour"]',
        ]
        
        offer_elements = []
        for selector in selectors_to_try:
            elements = soup.select(selector)
            if elements:
                offer_elements = elements
                if self.debug:
                    print(f"Found {len(elements)} elements with selector: {selector}")
                break
        
        if not offer_elements and self.debug:
            print("No offer elements found with any selector")
            self.save_debug_html(html_content, "teztour_debug.html")
        
        for element in offer_elements:
            try:
                # Extract title (hotel name)
                title_elem = element.find(['h2', 'h3', 'h4', 'a'])
                if not title_elem:
                    title_elem = element.find(string=True)
                title = title_elem.get_text(strip=True) if title_elem else ""
                
                # Extract link
                link_elem = element.find('a', href=True)
                link = link_elem['href'] if link_elem else ""
                if link and not link.startswith('http'):
                    link = f"https://www.teztour.bg{link}"
                
                # Extract price
                price_elem = element.find(['span', 'div', 'p'], class_=re.compile(r'price|cost|amount', re.I))
                if not price_elem:
                    # Look for € or лв in text
                    price_elem = element.find(string=re.compile(r'\d+\s*(лв|EUR|€)', re.I))
                    if price_elem:
                        price_elem = price_elem.parent
                price = self.parse_price(price_elem.get_text(strip=True) if price_elem else "")
                
                # Extract dates
                date_elem = element.find(['span', 'div', 'p'], class_=re.compile(r'date|period|night', re.I))
                if not date_elem:
                    # Look for date patterns
                    date_elem = element.find(string=re.compile(r'\d{1,2}\.\d{1,2}|нощувки', re.I))
                    if date_elem:
                        date_elem = date_elem.parent
                all_text = element.get_text(strip=True)
                dates = self.parse_dates(date_elem.get_text(strip=True) if date_elem else all_text)
                
                # Use provided destination name, fall back to extraction if needed
                destination = destination_name if destination_name != "Unknown" else self.extract_destination(title, all_text)
                
                # Only add if we have at least title
                if title and len(title) > 3:
                    offer = TeztourOffer(
                        title=title,
                        link=link,
                        price=price,
                        dates=dates,
                        destination=destination,
                        scraped_at=datetime.now().isoformat()
                    )
                    offers.append(offer)
                    
            except Exception as e:
                if self.debug:
                    print(f"Error parsing offer: {e}")
                continue
        
        return offers
    
    async def scrape(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Main scraping logic - discover destinations first, then scrape each one"""
        all_offers = []
        
        # Discover all destinations
        destinations = await self.discover_destinations()
        
        if not destinations:
            if self.debug:
                print("No destinations found, falling back to main page")
            # Fallback to main page if no destinations discovered
            html_content = await self.fetch_page(
                self.base_url,
                wait_for_selector='body',
                timeout=60000
            )
            await self.scroll_to_bottom(scroll_pause_time=1.5, max_scrolls=5)
            try:
                await self.click_load_more('button:has-text("ПОКАЖИ ОЩЕ")', max_clicks=3, wait_time=2.0)
            except:
                pass
            html_content = await self.page.content()
            offers = await self.extract_offers_from_page(html_content)
            all_offers.extend(offers)
        else:
            # Scrape each destination
            for i, destination in enumerate(destinations):
                dest_offers = await self.scrape_destination(destination)
                all_offers.extend(dest_offers)
                
                if self.debug:
                    print(f"Progress: {i+1}/{len(destinations)} destinations, {len(all_offers)} total offers")
                
                # Apply limit if specified and reached
                if limit and len(all_offers) >= limit:
                    all_offers = all_offers[:limit]
                    break
                
                # Small delay between destinations
                await asyncio.sleep(0.5)
        
        if self.debug:
            print(f"\nTotal offers collected: {len(all_offers)}")
        
        # Apply limit if not already applied
        if limit and len(all_offers) > limit:
            all_offers = all_offers[:limit]
        
        # Convert to dictionaries
        return [asdict(offer) for offer in all_offers]


if __name__ == "__main__":
    # Use the main page instead of best offers
    BASE_URL = "https://www.teztour.bg/"
    OUTPUT_FILE = "teztour.json"
    
    import asyncio
    asyncio.run(run_scraper(
        TeztourScraper,
        BASE_URL,
        OUTPUT_FILE,
        "Teztour.bg travel offers scraper"
    ))
