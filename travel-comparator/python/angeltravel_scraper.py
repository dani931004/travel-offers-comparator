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

    def load_and_process_existing_data(self, source_file: str) -> List[AngelTravelOffer]:
        """
        Load and process existing Angel Travel scraped data.
        Converts the complex structure to simplified offer format.
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

            # Extract dates
            dates_raw = item.get('dates')
            if dates_raw and dates_raw != 'None':
                offer.dates = str(dates_raw).strip()
            else:
                # Try to extract from title or program_info
                title_text = offer.title.lower()
                
                # Look for date patterns in title
                date_patterns = [
                    r'(\d{1,2}[./-]\d{1,2}[./-]\d{4})\s*-\s*(\d{1,2}[./-]\d{1,2}[./-]\d{4})',
                    r'(\d{1,2}[./-]\d{1,2}[./-]\d{4})',
                ]
                
                for pattern in date_patterns:
                    match = re.search(pattern, offer.title)
                    if match:
                        offer.dates = match.group(0)
                        break
                
                # If no dates found, leave empty
                if not offer.dates:
                    offer.dates = ""

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
        return unique_offers

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
    output_file = "/home/dani/Desktop/Organizer/angeltravel.json"

    # Allow custom paths from command line
    if len(sys.argv) > 1:
        source_file = sys.argv[1]
    if len(sys.argv) > 2:
        output_file = sys.argv[2]

    scraper = AngelTravelScraper()
    offers = scraper.load_and_process_existing_data(source_file)

    if offers:
        await scraper.save_results(output_file)

    print("\n=== SCRAPE COMPLETE ===")
    print(f"Total offers: {len(offers)}")


if __name__ == "__main__":
    import sys
    asyncio.run(main())
