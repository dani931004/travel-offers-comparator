#!/usr/bin/env python3
"""
Luxtravel.bg Travel Offers Scraper
Extracts travel offers from luxtravel.bg and saves them to JSON.
"""

import asyncio
import aiohttp
import aiofiles
from bs4 import BeautifulSoup
from datetime import datetime
from pathlib import Path
from dataclasses import dataclass, asdict
from typing import List, Optional
import re
import json


@dataclass
class LuxtravelOffer:
    """Data class for Luxtravel.bg travel offers"""
    title: str
    link: str
    price: str
    dates: str
    destination: str
    scraped_at: str


class LuxtravelScraper:
    """Async scraper for Luxtravel.bg travel offers"""
    
    BASE_URL = "https://luxtravel.bg"
    OFFERS_URL = BASE_URL
    
    def __init__(self, debug: bool = False, limit: Optional[int] = None):
        """
        Initialize the scraper.
        
        Args:
            debug: If True, save debug HTML files
            limit: Maximum number of offers to scrape (None for all)
        """
        self.debug = debug
        self.limit = limit
        self.session: Optional[aiohttp.ClientSession] = None
        self.offers: List[LuxtravelOffer] = []
        self.seen_urls = set()
        
    async def __aenter__(self):
        """Async context manager entry"""
        timeout = aiohttp.ClientTimeout(total=30)
        self.session = aiohttp.ClientSession(timeout=timeout)
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.session:
            await self.session.close()
            
    async def fetch_page(self, url: str) -> Optional[str]:
        """
        Fetch a page with error handling.
        
        Args:
            url: The URL to fetch
            
        Returns:
            HTML content or None if error
        """
        try:
            async with self.session.get(url) as response:
                if response.status == 200:
                    return await response.text()
                else:
                    print(f"Error fetching {url}: Status {response.status}")
                    return None
        except asyncio.TimeoutError:
            print(f"Timeout fetching {url}")
            return None
        except Exception as e:
            print(f"Error fetching {url}: {e}")
            return None
            
    async def save_debug_html(self, html: str, filename: str):
        """Save HTML to debug file"""
        if self.debug:
            debug_dir = Path("dev")
            debug_dir.mkdir(exist_ok=True)
            filepath = debug_dir / filename
            async with aiofiles.open(filepath, 'w', encoding='utf-8') as f:
                await f.write(html)
            print(f"Saved debug HTML to {filepath}")
            
    def parse_price(self, price_text: str) -> str:
        """
        Extract price from text.
        
        Args:
            price_text: Text containing price info
            
        Returns:
            Formatted price string
        """
        # Try to extract EUR price first
        eur_match = re.search(r'([\d\s,\.]+)\s*€', price_text)
        if eur_match:
            price = eur_match.group(1).strip().replace(' ', '').replace(',', '.')
            return f"{price} EUR"
        
        # Try to extract BGN price
        bgn_match = re.search(r'([\d\s,\.]+)\s*лв', price_text)
        if bgn_match:
            price = bgn_match.group(1).strip().replace(' ', '').replace(',', '.')
            return f"{price} BGN"
            
        return price_text.strip()
        
    def parse_dates(self, date_text: str) -> str:
        """
        Extract and format dates.
        
        Args:
            date_text: Text containing date info
            
        Returns:
            Formatted date range string
        """
        # Look for dates in various formats
        dates = re.findall(r"\b(\d{1,2}\.\d{1,2}\.\d{4})\b", date_text)
        if len(dates) >= 2:
            return f"{dates[0]} - {dates[-1]}"
        elif len(dates) == 1:
            return dates[0]
            
        return date_text.strip()
        
    def extract_destination(self, title: str, description: str = "") -> str:
        """
        Extract destination from title or description.
        
        Args:
            title: Offer title
            description: Offer description
            
        Returns:
            Destination name
        """
        text = f"{title} {description}".lower()
        
        # Common destinations
        destinations = [
            # Countries
            'египет', 'дубай', 'испания', 'турция', 'гърция', 'италия',
            'франция', 'португалия', 'хърватия', 'черна гора', 'албания',
            'кипър', 'малдиви', 'тайланд', 'сейшели', 'занзибар', 'мавриций',
            'доминикана', 'мексико', 'куба', 'йордания', 'мароко', 'малта',
            # Regions/cities commonly in titles
            'хургада', 'шарм', 'анталия', 'бодрум', 'родос', 'крит',
            'тенерифе', 'малорка', 'барселона', 'рим', 'париж', 'дубровник',
            'будва', 'котор', 'санторини', 'миконос', 'истамбул', 'лефкада', 'алания', 'памуккале'
        ]
        
        for dest in destinations:
            if dest in text:
                return dest.capitalize()
                
        return "Unknown"
        
    async def extract_offers_from_page(self, html: str, page_num: int = 1) -> List[LuxtravelOffer]:
        """
        Extract offers from the Luxtravel homepage sections.
        
        Returns:
            List of LuxtravelOffer objects
        """
        soup = BeautifulSoup(html, 'html.parser')
        offers: List[LuxtravelOffer] = []

        # Target concrete card structure observed in debug HTML
        cards = soup.select('div.col-offer a.offer-item')
        print(f"Found {len(cards)} offer cards on page {page_num}")

        for idx, link_elem in enumerate(cards):
            if self.limit and len(self.offers) >= self.limit:
                break
            try:
                # Link
                href = link_elem.get('href', '').strip()
                if not href:
                    continue
                if any(skip in href.lower() for skip in ['mailto:', 'tel:', 'javascript:', '#', 'facebook', 'instagram', 'twitter']):
                    continue
                if not href.startswith('http'):
                    href = self.BASE_URL + (href if href.startswith('/') else f"/{href}")

                if href in self.seen_urls:
                    continue
                self.seen_urls.add(href)

                # Title
                title_el = link_elem.select_one('div.title span')
                title = title_el.get_text(strip=True) if title_el else link_elem.get('title', '').strip() or link_elem.get_text(strip=True)
                if len(title) < 5:
                    continue

                # Price
                price_el = link_elem.select_one('div.price-wrap div.price')
                price_text = price_el.get_text(separator=' ', strip=True) if price_el else link_elem.get_text(separator=' ', strip=True)
                price = self.parse_price(price_text)

                # Dates: find the day-night block labeled with 'Дати'
                dates_text = ''
                for dn in link_elem.select('div.box_bottom div.day-night'):
                    label = dn.select_one('span.over')
                    if label and ('Дати' in label.get_text() or 'дати' in label.get_text().lower()):
                        spans = dn.select('span')
                        if len(spans) >= 2:
                            dates_text = spans[-1].get_text(strip=True)
                        else:
                            dates_text = dn.get_text(separator=' ', strip=True)
                        break
                if not dates_text:
                    # Fallback to any date-like text in the card
                    dates_text = link_elem.get_text(separator=' ', strip=True)
                dates = self.parse_dates(dates_text)

                destination = self.extract_destination(title, link_elem.get_text(separator=' ', strip=True))

                offer = LuxtravelOffer(
                    title=title,
                    link=href,
                    price=price,
                    dates=dates,
                    destination=destination,
                    scraped_at=datetime.now().isoformat()
                )

                offers.append(offer)

                if self.debug and idx < 3:
                    await self.save_debug_html(str(link_elem), f"debug_luxtravel_offer_{page_num}_{idx}.html")
            except Exception as e:
                print(f"Error extracting offer from element {idx}: {e}")
                continue

        return offers
        
    async def scrape_offers(self):
        """Main scraping logic"""
        print(f"Starting Luxtravel.bg scraper...")
        print(f"Debug mode: {self.debug}, Limit: {self.limit or 'No limit'}")
        
        # Fetch main offers page
        html = await self.fetch_page(self.OFFERS_URL)
        if not html:
            print("Failed to fetch offers page")
            return
            
        if self.debug:
            await self.save_debug_html(html, "luxtravel_offers_page.html")
            
        # Extract offers from first page
        page_offers = await self.extract_offers_from_page(html, 1)
        self.offers.extend(page_offers)
        
        print(f"Scraped {len(self.offers)} total offers")
        
    async def save_results(self, output_file: str = "luxtravel.json"):
        """
        Save scraped offers to JSON file.
        
        Args:
            output_file: Output filename
        """
        output_path = Path(output_file)
        
        # Convert offers to dicts
        offers_data = [asdict(offer) for offer in self.offers]
        
        # Save to JSON
        async with aiofiles.open(output_path, 'w', encoding='utf-8') as f:
            await f.write(json.dumps(offers_data, ensure_ascii=False, indent=2))
            
        print(f"Saved {len(offers_data)} offers to {output_path}")
        

async def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Scrape travel offers from Luxtravel.bg')
    parser.add_argument('--debug', action='store_true', help='Enable debug mode')
    parser.add_argument('--limit', type=int, default=20, help='Limit number of offers (default: 20 for testing)')
    parser.add_argument('--output', type=str, default='luxtravel.json', help='Output file path')
    
    args = parser.parse_args()
    
    async with LuxtravelScraper(debug=args.debug, limit=args.limit) as scraper:
        await scraper.scrape_offers()
        await scraper.save_results(args.output)
        

if __name__ == "__main__":
    asyncio.run(main())
