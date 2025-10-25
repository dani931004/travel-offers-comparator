#!/usr/bin/env python3
"""
Angel Travel Scraper - Comprehensive scraper for angeltravel.bg

This scraper extracts travel offers from Angel Travel, a Bulgarian travel agency.
Similar to Aratour, it organizes offers by destination and travel type.

Features:
- Discovers all destinations and categories from main site structure
- Extracts offers from existing scraped data (iframe-based offers)
- Parses offer details, prices, and dates
- Handles Bulgarian language content
- Outputs structured JSON data with only required fields
"""

import asyncio
import json
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional, Set, Any
from dataclasses import dataclass, field
import re

import aiohttp
from bs4 import BeautifulSoup

@dataclass
class AngelTravelOffer:
    """Data structure for Angel Travel offers with basic information."""
    title: str = ""
    link: str = ""
    price: str = ""
    dates: str = ""  # Travel dates
    destination: str = ""
    scraped_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict[str, Any]:
        """Convert offer to dictionary for JSON serialization."""
        return {
            'title': self.title,
            'link': self.link,
            'price': self.price,
            'dates': self.dates,
            'destination': self.destination,
            'scraped_at': self.scraped_at
        }


class AngelTravelScraper:
    """Scraper for Angel Travel travel offers."""

    def __init__(self):
        self.scraped_offers: List[AngelTravelOffer] = []
        self.processed_urls: Set[str] = set()
        self.session: Optional[aiohttp.ClientSession] = None

    async def __aenter__(self):
        """Async context manager entry."""
        self.session = aiohttp.ClientSession(
            headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'bg,en-US;q=0.7,en;q=0.3',
                'Accept-Encoding': 'gzip, deflate, br',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
            }
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.session:
            await self.session.close()

    async def fetch_dates_from_url(self, url: str) -> str:
        """
        Fetch and extract dates from an offer URL.
        If dates not found on main page, tries to fetch from hotel pages.
        Returns formatted date string or empty string if not found.
        """
        if not url or not self.session:
            return ""

        try:
            async with self.session.get(url, timeout=aiohttp.ClientTimeout(total=30)) as response:
                if response.status != 200:
                    return ""

                content = await response.read()
                
                # Try different encodings
                try:
                    text = content.decode('utf-8')
                except UnicodeDecodeError:
                    try:
                        text = content.decode('windows-1251')
                    except UnicodeDecodeError:
                        try:
                            text = content.decode('iso-8859-1')
                        except:
                            return ""

                soup = BeautifulSoup(text, 'html.parser')
                
                # Extract all text from the page
                page_text = soup.get_text()
                
                # Look for date patterns DD.MM.YYYY
                date_pattern = r'\d{1,2}\.\d{1,2}\.\d{4}'
                all_dates = re.findall(date_pattern, page_text)
                
                if all_dates:
                    # Remove duplicates while preserving order
                    seen = set()
                    unique_dates = []
                    for d in all_dates:
                        if d not in seen:
                            seen.add(d)
                            unique_dates.append(d)
                    
                    if len(unique_dates) == 1:
                        return unique_dates[0]
                    elif len(unique_dates) > 1:
                        # Sort dates and create range
                        try:
                            from datetime import datetime
                            parsed_dates = [datetime.strptime(d, "%d.%m.%Y") for d in unique_dates]
                            parsed_dates.sort()
                            first_date = parsed_dates[0].strftime("%d.%m.%Y")
                            last_date = parsed_dates[-1].strftime("%d.%m.%Y")
                            return f"{first_date} - {last_date}"
                        except:
                            return f"{unique_dates[0]} - {unique_dates[-1]}"
                
                # No dates found on main page - try hotel pages
                # Look for hotel links
                hotel_links = []
                for a in soup.find_all('a', href=True):
                    href = a['href']
                    if 'hotel-pochivka.php' in href:
                        hotel_links.append(href)
                
                if hotel_links:
                    # Try first hotel link
                    hotel_href = hotel_links[0]
                    # Make absolute URL
                    if not hotel_href.startswith('http'):
                        base_url = 'https://iframe.peakview.bg/'
                        hotel_url = base_url + hotel_href
                    else:
                        hotel_url = hotel_href
                    
                    # Fetch hotel page
                    dates_from_hotel = await self.fetch_dates_from_hotel_page(hotel_url)
                    if dates_from_hotel:
                        return dates_from_hotel
                
                return ""

        except asyncio.TimeoutError:
            print(f"  ⚠ Timeout fetching: {url[:80]}...")
            return ""
        except Exception as e:
            print(f"  ⚠ Error fetching {url[:80]}...: {str(e)[:50]}")
            return ""

    async def fetch_dates_from_hotel_page(self, url: str) -> str:
        """
        Fetch dates specifically from a hotel page.
        Returns formatted date string or empty string if not found.
        """
        try:
            async with self.session.get(url, timeout=aiohttp.ClientTimeout(total=30)) as response:
                if response.status != 200:
                    return ""

                content = await response.read()
                
                # Try different encodings
                try:
                    text = content.decode('utf-8')
                except UnicodeDecodeError:
                    try:
                        text = content.decode('windows-1251')
                    except UnicodeDecodeError:
                        try:
                            text = content.decode('iso-8859-1')
                        except:
                            return ""

                soup = BeautifulSoup(text, 'html.parser')
                
                # Look for date elements (td.date, div.col_dates, etc.)
                date_elements = soup.find_all(['td', 'span', 'div'], class_=re.compile('date', re.I))
                
                dates = []
                for elem in date_elements:
                    text = elem.get_text(strip=True)
                    date_pattern = r'\d{1,2}\.\d{1,2}\.\d{4}'
                    found = re.findall(date_pattern, text)
                    dates.extend(found)
                
                if dates:
                    # Remove duplicates
                    seen = set()
                    unique_dates = []
                    for d in dates:
                        if d not in seen:
                            seen.add(d)
                            unique_dates.append(d)
                    
                    if len(unique_dates) == 1:
                        return unique_dates[0]
                    elif len(unique_dates) > 1:
                        # Sort and create range
                        try:
                            from datetime import datetime
                            parsed_dates = [datetime.strptime(d, "%d.%m.%Y") for d in unique_dates]
                            parsed_dates.sort()
                            first_date = parsed_dates[0].strftime("%d.%m.%Y")
                            last_date = parsed_dates[-1].strftime("%d.%m.%Y")
                            return f"{first_date} - {last_date}"
                        except:
                            return f"{unique_dates[0]} - {unique_dates[-1]}"
                
                return ""

        except Exception as e:
            return ""

    async def load_and_process_existing_data(self, source_file: str) -> List[AngelTravelOffer]:
        """
        Load and process existing Angel Travel scraped data.
        Converts the complex structure to simplified offer format.
        Fetches dates from offer URLs when missing.
        """
        print("=== ANGEL TRAVEL SCRAPER ===")
        print(f"Loading existing data from: {source_file}")

        try:
            with open(source_file, 'r', encoding='utf-8') as f:
                raw_data = json.load(f)
        except FileNotFoundError:
            print(f"✗ Source file not found: {source_file}")
            return []
        except json.JSONDecodeError as e:
            print(f"✗ Error parsing JSON: {e}")
            return []

        print(f"✓ Loaded {len(raw_data)} raw offers")

        offers = []
        for item in raw_data:
            offer = AngelTravelOffer()

            # Extract title
            offer.title = item.get('title', '').strip()

            # Extract link
            offer.link = item.get('link', '').strip()

            # Extract and clean price
            price_raw = item.get('price', '')
            if price_raw:
                # Extract just the first price (in лв)
                price_match = re.search(r'([\d.,]+)\s*лв', str(price_raw))
                if price_match:
                    offer.price = f"{price_match.group(1)} лв"
                else:
                    offer.price = str(price_raw).strip()

            # Extract dates and format as date range
            dates_raw = item.get('dates')
            dates_found = False
            
            if dates_raw and dates_raw != 'None':
                dates_str = str(dates_raw).strip()
                # Parse multiple dates and create range from first to last
                date_pattern = r'\d{1,2}\.\d{1,2}\.\d{4}'
                all_dates = re.findall(date_pattern, dates_str)
                
                if all_dates:
                    if len(all_dates) == 1:
                        offer.dates = all_dates[0]
                    else:
                        # Sort dates and create range
                        try:
                            from datetime import datetime
                            parsed_dates = [datetime.strptime(d, "%d.%m.%Y") for d in all_dates]
                            parsed_dates.sort()
                            first_date = parsed_dates[0].strftime("%d.%m.%Y")
                            last_date = parsed_dates[-1].strftime("%d.%m.%Y")
                            offer.dates = f"{first_date} - {last_date}"
                        except:
                            # If parsing fails, use first and last from the list
                            offer.dates = f"{all_dates[0]} - {all_dates[-1]}"
                    dates_found = True
                else:
                    offer.dates = dates_str
                    dates_found = bool(dates_str)
            
            if not dates_found:
                # Try to extract from title
                date_patterns = [
                    r'(\d{1,2}[./-]\d{1,2}[./-]\d{4})\s*-\s*(\d{1,2}[./-]\d{1,2}[./-]\d{4})',
                    r'(\d{1,2}[./-]\d{1,2}[./-]\d{4})',
                ]
                
                for pattern in date_patterns:
                    match = re.search(pattern, offer.title)
                    if match:
                        offer.dates = match.group(0)
                        dates_found = True
                        break
            
            # Mark for URL fetching if still no dates
            if not dates_found:
                offer.dates = "FETCH_FROM_URL"

            # Extract and normalize destination
            destination_raw = item.get('destination', '')
            if destination_raw:
                # Normalize destination names to Bulgarian
                destination_map = {
                    'Albania': 'Албания',
                    'Austria': 'Австрия',
                    'Belgium': 'Белгия',
                    'Bosnia And Herzegovina': 'Босна и Херцеговина',
                    'Croatia': 'Хърватия',
                    'Czech Republic': 'Чехия',
                    'Denmark': 'Дания',
                    'Egypt': 'Египет',
                    'France': 'Франция',
                    'Germany': 'Германия',
                    'Greece': 'Гърция',
                    'Ireland': 'Ирландия',
                    'Italy': 'Италия',
                    'Malta': 'Малта',
                    'Netherlands': 'Холандия',
                    'Portugal': 'Португалия',
                    'Romania': 'Румъния',
                    'Serbia': 'Сърбия',
                    'Spain': 'Испания',
                    'Sweden': 'Швеция',
                    'Switzerland': 'Швейцария',
                    'Tunisia': 'Тунис',
                    'Turkey': 'Турция',
                    'United Kingdom': 'Великобритания',
                    'Turkey': 'Турция',
                    'Bulgaria': 'България',
                    'Montenegro': 'Черна гора',
                    'Slovenia': 'Словения',
                    'Poland': 'Полша',
                    'Hungary': 'Унгария',
                    'Slovakia': 'Словакия',
                    'Ukraine': 'Украйна',
                    'Moldova': 'Молдова',
                    'Cyprus': 'Кипър',
                    'Morocco': 'Мароко',
                    'Israel': 'Израел',
                    'Jordan': 'Йордания',
                    'Lebanon': 'Ливан',
                    'Dubai': 'Дубай',
                    'UAE': 'ОАЕ',
                    'Thailand': 'Тайланд',
                    'Vietnam': 'Виетнам',
                    'China': 'Китай',
                    'Japan': 'Япония',
                    'South Korea': 'Южна Корея',
                    'India': 'Индия',
                    'Indonesia': 'Индонезия',
                    'Malaysia': 'Малайзия',
                    'Singapore': 'Сингапур',
                    'Philippines': 'Филипини',
                    'Australia': 'Австралия',
                    'New Zealand': 'Нова Зеландия',
                    'USA': 'САЩ',
                    'Canada': 'Канада',
                    'Mexico': 'Мексико',
                    'Cuba': 'Куба',
                    'Brazil': 'Бразилия',
                    'Argentina': 'Аржентина',
                    'Peru': 'Перу',
                    'Chile': 'Чили',
                    'South Africa': 'Южна Африка',
                    'Kenya': 'Кения',
                    'Tanzania': 'Танзания',
                    'Madagascar': 'Мадагаскар',
                }
                
                # Handle special cases
                if destination_raw in destination_map:
                    offer.destination = destination_map[destination_raw]
                elif destination_raw in ['Barcelona', 'Madrid', 'Valencia', 'Seville']:
                    offer.destination = 'Испания'
                elif destination_raw in ['Rome', 'Milan', 'Venice', 'Florence', 'Naples', 'Sicily', 'Calabria', 'Campania', 'Tuscany', 'Toscana', 'Pulia', 'Puglia', 'Lake Garda', 'Italian Riviera', 'Rimini', 'Excursions Italy']:
                    offer.destination = 'Италия'
                elif destination_raw in ['Paris', 'Lyon', 'Nice', 'Côte D\'Azur', 'French Riviera']:
                    offer.destination = 'Франция'
                elif destination_raw in ['Corfu', 'Crete', 'Rhodes', 'Santorini', 'Mykonos', 'Zakynthos', 'Thassos', 'Halkidiki', 'Peloponnese', 'Athens', 'Thessaloniki', 'Bus Tours']:
                    offer.destination = 'Гърция'
                elif destination_raw in ['Benidorm', 'Costa Brava', 'Costa Del Sol', 'Costa Del Azahar', 'Costa Dorada', 'Mallorca', 'Palma De Mallorca', 'La Manga', 'Ibiza', 'Canary Islands', 'Tenerife', 'Excursions Spain']:
                    offer.destination = 'Испания'
                elif destination_raw in ['Antalya', 'Side', 'Alanya', 'Belek', 'Bodrum', 'Marmaris', 'Kusadasi', 'Istanbul', 'Cappadocia']:
                    offer.destination = 'Турция'
                elif destination_raw in ['Sharm El Sheikh', 'Hurghada', 'Marsa Alam', 'Cairo', 'Alexandria']:
                    offer.destination = 'Египет'
                elif destination_raw in ['Latvijas Republika', 'Latvia']:
                    offer.destination = 'Латвия'
                elif destination_raw in ['North Macedonia', 'Macedonia']:
                    offer.destination = 'Северна Македония'
                else:
                    # Keep original if no mapping found
                    offer.destination = destination_raw

            # Only add if we have at least title and link
            if offer.title and offer.link:
                offers.append(offer)

        # Remove duplicates based on title + link combination
        seen = set()
        unique_offers = []
        for offer in offers:
            key = (offer.title, offer.link)
            if key not in seen:
                seen.add(key)
                unique_offers.append(offer)

        duplicates_removed = len(offers) - len(unique_offers)
        if duplicates_removed > 0:
            print(f"✓ Removed {duplicates_removed} duplicate offers")

        self.scraped_offers = unique_offers
        print(f"✓ Total unique offers processed: {len(unique_offers)}")
        
        # Now fetch dates from URLs for offers marked FETCH_FROM_URL
        offers_needing_dates = [o for o in self.scraped_offers if o.dates == "FETCH_FROM_URL"]
        if offers_needing_dates:
            print(f"\n⚙ Fetching dates from {len(offers_needing_dates)} offer URLs...")
            await self.fetch_missing_dates(offers_needing_dates)
        
        return unique_offers

    async def fetch_missing_dates(self, offers: List[AngelTravelOffer]):
        """Fetch dates from offer URLs in batches."""
        batch_size = 10  # Process 10 URLs at a time to avoid overwhelming the server
        total = len(offers)
        fetched = 0
        failed = 0
        
        for i in range(0, total, batch_size):
            batch = offers[i:i + batch_size]
            tasks = []
            
            for offer in batch:
                tasks.append(self.fetch_dates_from_url(offer.link))
            
            # Fetch batch concurrently
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Update offers with fetched dates
            for offer, result in zip(batch, results):
                if isinstance(result, str) and result:
                    offer.dates = result
                    fetched += 1
                else:
                    offer.dates = ""  # Clear the marker if fetch failed
                    failed += 1
            
            # Progress update
            processed = min(i + batch_size, total)
            print(f"  Processed {processed}/{total} URLs (✓ {fetched} found, ✗ {failed} not found)")
            
            # Small delay between batches to be polite
            if i + batch_size < total:
                await asyncio.sleep(1)
        
        print(f"✓ Date fetching complete: {fetched} dates found, {failed} not found")


    async def save_results(self, output_file: str):
        """Save scraped data to JSON file with only required fields."""
        # Save JSON with only required fields
        offers_data = [offer.to_dict() for offer in self.scraped_offers]

        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(offers_data, f, ensure_ascii=False, indent=2)

        print(f"✓ Exported to JSON: {output_file}")


async def main():
    """Main scraping function."""
    import sys

    # Default paths
    source_file = "/home/dani/Desktop/Organizer/angel_travel_scrape.json"
    output_file = "/home/dani/Desktop/Organizer/angel_travel_scrape.json"

    # Allow custom paths from command line
    if len(sys.argv) > 1:
        source_file = sys.argv[1]
    if len(sys.argv) > 2:
        output_file = sys.argv[2]

    # Use async context manager to handle session lifecycle
    async with AngelTravelScraper() as scraper:
        offers = await scraper.load_and_process_existing_data(source_file)

        if offers:
            await scraper.save_results(output_file)

        print("\n=== SCRAPE COMPLETE ===")
        print(f"Total offers: {len(offers)}")
        
        # Count offers with/without dates
        with_dates = sum(1 for o in offers if o.dates and o.dates != "")
        without_dates = len(offers) - with_dates
        print(f"Offers with dates: {with_dates}")
        print(f"Offers without dates: {without_dates}")


if __name__ == "__main__":
    import sys
    asyncio.run(main())
