#!/usr/bin/env python3
"""
Aventura.bg Travel Offers Scraper
Extracts travel offers from aventura.bg and saves them to JSON.
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
class AventuraOffer:
    """Data class for Aventura.bg travel offers"""
    title: str
    link: str
    price: str
    dates: str
    destination: str
    scraped_at: str


class AventuraScraper:
    """Async scraper for Aventura.bg travel offers"""
    
    BASE_URL = "https://aventura.bg"
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
        self.offers: List[AventuraOffer] = []
        self.seen_urls = set()
        
    async def __aenter__(self):
        """Async context manager entry"""
        timeout = aiohttp.ClientTimeout(total=30)
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        self.session = aiohttp.ClientSession(timeout=timeout, headers=headers)
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
        # Look for dates in DD.MM.YYYY or DD.MM format, but avoid price-like patterns
        # More specific regex to avoid matching prices like "05.61"
        dates = re.findall(r'\b\d{1,2}\.\d{1,2}(?:\.\d{2,4})?\b', date_text)
        
        # Filter out dates that look like prices (very small numbers)
        valid_dates = []
        for date in dates:
            parts = date.split('.')
            if len(parts) >= 2:
                day = int(parts[0])
                month = int(parts[1])
                # Basic validation: day 1-31, month 1-12
                if 1 <= day <= 31 and 1 <= month <= 12:
                    valid_dates.append(date)
        
        if len(valid_dates) >= 2:
            return f"{valid_dates[0]} - {valid_dates[-1]}"
        elif len(valid_dates) == 1:
            return valid_dates[0]
            
        return ""
        
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
            'египет', 'дубай', 'испания', 'турция', 'гърция', 'италия',
            'франция', 'португалия', 'хърватия', 'черна гора', 'albania',
            'албания', 'кипър', 'малдиви', 'тайланд', 'бали', 'сейшели',
            'занзибар', 'мавриций', 'доминикана', 'мексико', 'куба',
            'хургада', 'шарм', 'анталия', 'бодрум', 'родос', 'крит',
            'тенерифе', 'малорка', 'барселона', 'рим', 'париж', 'дубровник',
            'будва', 'котор', 'санторини', 'миконос'
        ]
        
        for dest in destinations:
            if dest in text:
                return dest.capitalize()
                
        return "Unknown"
        
    async def extract_offers_from_page(self, html: str, page_num: int = 1) -> List[AventuraOffer]:
        """
        Extract offers from an offers listing page.
        
        Args:
            html: HTML content
            page_num: Page number for debugging
            
        Returns:
            List of AventuraOffer objects
        """
        soup = BeautifulSoup(html, 'html.parser')
        offers = []
        
        # Find individual offer links (not containers)
        offer_links = soup.find_all('a', href=re.compile(r'^(pochivka|ekskurzia)/'))
        
        print(f"Found {len(offer_links)} potential offer links on page {page_num}")
        
        for idx, link_elem in enumerate(offer_links):
            if self.limit and len(self.offers) >= self.limit:
                break
                
            try:
                link = link_elem.get('href', '')
                if not link:
                    continue
                    
                # Skip duplicates
                if link in self.seen_urls:
                    continue
                self.seen_urls.add(link)
                
                if not link.startswith('http'):
                    link = self.BASE_URL + link if link.startswith('/') else f"{self.BASE_URL}/{link}"
                
                # Get text content from the link element
                text_content = link_elem.get_text(separator=' ', strip=True)
                
                # Extract title - look for specific classes or patterns
                title = ""
                
                # Try to find title in specific div classes
                title_elem = link_elem.find(['div'], class_=re.compile(r'tleft-title|tright-title|tr-hotel'))
                if title_elem:
                    title = title_elem.get_text(separator=' ', strip=True)
                else:
                    # Fallback: use the link text
                    title = text_content
                
                # Clean up title - remove price info
                title = re.sub(r'\s*от\s*\d+[\d\s,\.]*€|\s*от\s*\d+[\d\s,\.]*лв.*', '', title).strip()
                
                # Skip if title is too short
                if len(title) < 5:
                    continue
                
                # Extract price - look for spans or specific patterns
                price = ""
                price_elem = link_elem.find('span')
                if price_elem:
                    price = self.parse_price(price_elem.get_text(strip=True))
                else:
                    # Look for price patterns in the text
                    price_match = re.search(r'(\d+[\d\s,\.]*)\s*€|(\d+[\d\s,\.]*)\s*лв', text_content)
                    if price_match:
                        price_text = price_match.group(1) or price_match.group(2)
                        price = self.parse_price(price_text + (' €' if price_match.group(1) else ' лв'))
                
                # Extract dates - look for date patterns in text or nearby elements
                dates = ""
                
                # Check if there are any date comments or hidden date divs
                date_div = link_elem.find_next('div', class_=re.compile(r'tr-date'))
                if date_div:
                    dates = self.parse_dates(date_div.get_text(strip=True))
                else:
                    # Look for date patterns in the text
                    dates = self.parse_dates(text_content)
                
                # Extract destination - look for location div or patterns
                destination = "Unknown"
                loc_elem = link_elem.find(['div'], class_=re.compile(r'tr-loc'))
                if loc_elem:
                    destination = loc_elem.get_text(strip=True)
                else:
                    # Try to extract from title or text
                    destination = self.extract_destination(title, text_content)
                
                # Create offer
                offer = AventuraOffer(
                    title=title,
                    link=link,
                    price=price,
                    dates=dates,
                    destination=destination,
                    scraped_at=datetime.now().isoformat()
                )
                
                offers.append(offer)
                
                if self.debug and idx < 3:
                    await self.save_debug_html(str(link_elem), f"debug_aventura_offer_{page_num}_{idx}.html")
                    
            except Exception as e:
                print(f"Error extracting offer from link {idx}: {e}")
                continue
                
        return offers
        
    async def scrape_offers(self):
        """Main scraping logic"""
        print(f"Starting Aventura.bg scraper...")
        print(f"Debug mode: {self.debug}, Limit: {self.limit or 'No limit'}")
        
        # Fetch main offers page
        html = await self.fetch_page(self.OFFERS_URL)
        if not html:
            print("Failed to fetch offers page")
            return
            
        if self.debug:
            await self.save_debug_html(html, "aventura_offers_page.html")
            
        # Extract offers from first page
        page_offers = await self.extract_offers_from_page(html, 1)
        self.offers.extend(page_offers)
        
        print(f"Scraped {len(self.offers)} total offers")
        
    async def save_results(self, output_file: str = "aventura.json"):
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
    
    parser = argparse.ArgumentParser(description='Scrape travel offers from Aventura.bg')
    parser.add_argument('--debug', action='store_true', help='Enable debug mode')
    parser.add_argument('--limit', type=int, default=20, help='Limit number of offers (default: 20 for testing)')
    parser.add_argument('--output', type=str, default='aventura.json', help='Output file path')
    
    args = parser.parse_args()
    
    async with AventuraScraper(debug=args.debug, limit=args.limit) as scraper:
        await scraper.scrape_offers()
        await scraper.save_results(args.output)
        

if __name__ == "__main__":
    asyncio.run(main())
