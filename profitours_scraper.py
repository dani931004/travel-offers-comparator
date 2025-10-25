#!/usr/bin/env python3
"""
Profitours.bg Travel Offers Scraper
Extracts travel offers from profitours.bg and saves them to JSON.
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
class ProftoursOffer:
    """Data class for Profitours.bg travel offers"""
    title: str
    link: str
    price: str
    dates: str
    destination: str
    scraped_at: str


class ProfitoursScraper:
    """Async scraper for Profitours.bg travel offers"""
    
    BASE_URL = "https://www.profitours.bg"
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
        self.offers: List[ProftoursOffer] = []
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
        """Extract price from text."""
        eur_match = re.search(r'([\d\s,\.]+)\s*€', price_text)
        if eur_match:
            price = eur_match.group(1).strip().replace(' ', '').replace(',', '.')
            return f"{price} EUR"
        
        bgn_match = re.search(r'([\d\s,\.]+)\s*лв', price_text)
        if bgn_match:
            price = bgn_match.group(1).strip().replace(' ', '').replace(',', '.')
            return f"{price} BGN"
            
        return price_text.strip()
        
    def parse_dates(self, date_text: str) -> str:
        """Extract and format dates."""
        dates = re.findall(r'\d{2}\.\d{2}\.?\d{0,4}', date_text)
        
        if len(dates) >= 2:
            return f"{dates[0]} - {dates[-1]}"
        elif len(dates) == 1:
            return dates[0]
            
        return date_text.strip()
        
    def extract_destination(self, title: str, description: str = "") -> str:
        """Extract destination from title or description."""
        text = f"{title} {description}".lower()
        
        destinations = [
            'египет', 'дубай', 'испания', 'турция', 'гърция', 'италия',
            'франция', 'португалия', 'хърватия', 'черна гора', 'albania',
            'албания', 'кипър', 'малдиви', 'тайланд', 'бали', 'сейшели',
            'занзибар', 'мавриций', 'доминикана', 'мексико', 'куба',
            'хургада', 'шарм', 'анталия', 'бодрум', 'родос', 'крит',
            'тенерифе', 'малорка', 'барселона', 'рим', 'париж', 'дубровник',
            'будва', 'котор', 'санторини', 'миконос', 'мадрид', 'лисабон'
        ]
        
        for dest in destinations:
            if dest in text:
                return dest.capitalize()
                
        return "Unknown"
        
    async def extract_offers_from_page(self, html: str, page_num: int = 1) -> List[ProftoursOffer]:
        """Extract offers from an offers listing page."""
        soup = BeautifulSoup(html, 'html.parser')
        offers = []
        
        offer_cards = soup.find_all('div', class_=re.compile(r'offer|tour|package|program|card|product', re.I))
        if not offer_cards:
            offer_cards = soup.find_all('article')
        if not offer_cards:
            all_links = soup.find_all('a', href=True)
            offer_cards = [link for link in all_links if any(keyword in link.get('href', '').lower() for keyword in ['/tour', '/offer', '/program', '/excurs', '/destination'])]
        
        print(f"Found {len(offer_cards)} potential offer elements on page {page_num}")
        
        for idx, card in enumerate(offer_cards):
            if self.limit and len(self.offers) >= self.limit:
                break
                
            try:
                if card.name == 'a':
                    link_elem = card
                else:
                    link_elem = card.find('a', href=True)
                    
                if not link_elem:
                    continue
                    
                link = link_elem.get('href', '')
                if not link:
                    continue
                    
                if any(skip in link.lower() for skip in ['mailto:', 'tel:', 'javascript:', '#', 'facebook', 'instagram', 'twitter']):
                    continue
                    
                if not link.startswith('http'):
                    link = self.BASE_URL + link if link.startswith('/') else f"{self.BASE_URL}/{link}"
                    
                if link in self.seen_urls:
                    continue
                self.seen_urls.add(link)
                
                if card.name == 'a':
                    parent = card.find_parent(['div', 'article', 'section'])
                    text_content = parent.get_text(separator=' ', strip=True) if parent else card.get_text(separator=' ', strip=True)
                else:
                    text_content = card.get_text(separator=' ', strip=True)
                
                title_elem = card.find(['h1', 'h2', 'h3', 'h4'], class_=re.compile(r'title|name|head', re.I))
                if not title_elem and card.name == 'a':
                    title = card.get_text(strip=True)
                elif title_elem:
                    title = title_elem.get_text(strip=True)
                else:
                    lines = [line.strip() for line in text_content.split('\n') if line.strip()]
                    title = lines[0] if lines else "No title"
                
                if len(title) < 5:
                    continue
                
                price_elem = card.find(['span', 'div', 'p'], class_=re.compile(r'price|cost|цена', re.I))
                if price_elem:
                    price = self.parse_price(price_elem.get_text(strip=True))
                else:
                    price_match = re.search(r'\d+[\s,]*€|\d+[\s,]*лв', text_content)
                    price = self.parse_price(price_match.group(0)) if price_match else ""
                
                date_elem = card.find(['span', 'div', 'p'], class_=re.compile(r'date|time|период|дат', re.I))
                if date_elem:
                    dates = self.parse_dates(date_elem.get_text(strip=True))
                else:
                    dates = self.parse_dates(text_content)
                
                destination = self.extract_destination(title, text_content)
                
                offer = ProftoursOffer(
                    title=title,
                    link=link,
                    price=price,
                    dates=dates,
                    destination=destination,
                    scraped_at=datetime.now().isoformat()
                )
                
                offers.append(offer)
                
                if self.debug and idx < 3:
                    await self.save_debug_html(str(card), f"debug_profitours_offer_{page_num}_{idx}.html")
                    
            except Exception as e:
                print(f"Error extracting offer from element {idx}: {e}")
                continue
                
        return offers
        
    async def scrape_offers(self):
        """Main scraping logic"""
        print(f"Starting Profitours.bg scraper...")
        print(f"Debug mode: {self.debug}, Limit: {self.limit or 'No limit'}")
        
        html = await self.fetch_page(self.OFFERS_URL)
        if not html:
            print("Failed to fetch offers page")
            return
            
        if self.debug:
            await self.save_debug_html(html, "profitours_offers_page.html")
            
        page_offers = await self.extract_offers_from_page(html, 1)
        self.offers.extend(page_offers)
        
        print(f"Scraped {len(self.offers)} total offers")
        
    async def save_results(self, output_file: str = "profitours.json"):
        """Save scraped offers to JSON file."""
        output_path = Path(output_file)
        offers_data = [asdict(offer) for offer in self.offers]
        
        async with aiofiles.open(output_path, 'w', encoding='utf-8') as f:
            await f.write(json.dumps(offers_data, ensure_ascii=False, indent=2))
            
        print(f"Saved {len(offers_data)} offers to {output_path}")
        

async def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Scrape travel offers from Profitours.bg')
    parser.add_argument('--debug', action='store_true', help='Enable debug mode')
    parser.add_argument('--limit', type=int, default=20, help='Limit number of offers (default: 20 for testing)')
    parser.add_argument('--output', type=str, default='profitours.json', help='Output file path')
    
    args = parser.parse_args()
    
    async with ProfitoursScraper(debug=args.debug, limit=args.limit) as scraper:
        await scraper.scrape_offers()
        await scraper.save_results(args.output)
        

if __name__ == "__main__":
    asyncio.run(main())
