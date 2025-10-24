#!/usr/bin/env python3
"""
Dari Tour Scraper - Comprehensive scraper for dari-tour.com

This scraper extracts travel offers from Dari Tour, a Bulgarian travel agency.
Unlike Aratour which organizes offers by destination, Dari Tour displays offers
directly on category pages and individual offer pages.

Features:
- Discovers offers from main page and category pages
- Extracts offer details from individual offer pages
- Parses offer information, prices, dates, and destinations
- Handles Bulgarian language content
- Outputs structured JSON data with only required fields
"""

import asyncio
import json
import csv
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional, Set, Any
from dataclasses import dataclass, field

import re

import aiohttp
import aiofiles
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse, unquote


@dataclass
class DariTourOffer:
    """Data structure for Dari Tour offers with basic information."""
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


class DariTourScraper:
    """Scraper for Dari Tour travel offers."""

    BASE_URL = "https://dari-tour.com"
    OUTPUT_DIR = Path(__file__).parent / "output"

    def __init__(self):
        self.session: Optional[aiohttp.ClientSession] = None
        self.scraped_offers: List[DariTourOffer] = []
        self.processed_urls: Set[str] = set()

    async def __aenter__(self):
        """Async context manager entry."""
        self.session = aiohttp.ClientSession(
            headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
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

    async def fetch_page(self, url: str) -> Optional[str]:
        """Fetch a page with error handling."""
        try:
            async with self.session.get(url, timeout=aiohttp.ClientTimeout(total=30)) as response:
                if response.status == 200:
                    # Try different encodings if UTF-8 fails
                    content = await response.read()
                    try:
                        text = content.decode('utf-8')
                    except UnicodeDecodeError:
                        try:
                            text = content.decode('windows-1251')
                        except UnicodeDecodeError:
                            try:
                                text = content.decode('iso-8859-5')
                            except UnicodeDecodeError:
                                text = content.decode('utf-8', errors='ignore')

                    print(f"✓ Fetched: {url} ({len(text)} chars)")
                    return text
                else:
                    print(f"✗ Failed to fetch {url}: HTTP {response.status}")
                    return None
        except Exception as e:
            print(f"✗ Error fetching {url}: {e}")
            return None

    def extract_offer_links(self, html: str) -> List[str]:
        """Extract offer URLs from a page."""
        soup = BeautifulSoup(html, 'html.parser')
        offer_urls = set()

        # Find all links that look like offers
        for a in soup.find_all('a', href=True):
            href = a['href']

            # Skip non-offer links
            if any(skip in href.lower() for skip in [
                'tel:', 'mailto:', 'javascript:', '#', 'facebook', 'instagram',
                'iskam-oferta', 'contact', 'about', 'privacy', 'terms'
            ]):
                continue

            # Skip hotel listing pages, calendar pages, and other non-offer pages
            if any(skip_pattern in href.lower() for skip_pattern in [
                '/hoteli/', '/kalendar/', '/calendar', '/karibski-ray'
            ]):
                continue

            # Only include actual offer pages (not calendar pages)
            if (any(offer_pattern in href.lower() for offer_pattern in [
                'ekskurzia', 'ekskurzii', 'pochivki', 'pochi'
            ]) and 'kalendar' not in href.lower()):
                full_url = urljoin(self.BASE_URL, href)
                if full_url not in offer_urls and full_url != self.BASE_URL:
                    offer_urls.add(full_url)

        return list(offer_urls)

    def extract_offers_from_page(self, html: str, page_url: str) -> List[DariTourOffer]:
        """Extract offers from a page (main page, category page, or individual offer page)."""
        soup = BeautifulSoup(html, 'html.parser')
        offers = []

        # Check if this is an individual offer page
        if self._is_individual_offer_page(page_url):
            offer = self._extract_single_offer(html, page_url)
            if offer:
                offers.append(offer)
            return offers

        # Extract offers from listing pages (main page, category pages)
        offer_cards = soup.find_all('div', class_=re.compile(r'col-offer|offer|tour'))

        for card in offer_cards:
            offer = DariTourOffer()

            # Extract link
            link_elem = card.find('a', href=True)
            if link_elem:
                href = link_elem['href']
                offer.link = urljoin(self.BASE_URL, href)
            else:
                continue

            # Extract title
            title_elem = card.find(['h1', 'h2', 'h3', 'h4', 'strong', 'b']) or card.find('div', class_='title')
            if title_elem:
                title_text = title_elem.get_text().strip()
                if title_text and len(title_text) > 5:
                    offer.title = title_text
            else:
                # Fallback: use link text or card text
                card_text = card.get_text().strip()
                lines = [line.strip() for line in card_text.split('\n') if line.strip() and len(line.strip()) > 5]
                if lines:
                    offer.title = lines[0][:150]

            # Extract price
            price_elem = card.find('div', class_='price')
            if price_elem:
                price_text = price_elem.get_text().strip()
                price_match = re.search(r'(\d+(?:,\d{3})*(?:\.\d{2})?)\s*лв', price_text)
                if price_match:
                    offer.price = price_match.group(0)

            # Extract dates
            card_text = card.get_text()
            date_matches = re.findall(r'\d{1,2}[./-]\d{1,2}[./-]\d{4}', card_text)
            if date_matches:
                if len(date_matches) == 1:
                    offer.dates = date_matches[0]
                else:
                    # Sort dates and create range
                    try:
                        parsed_dates = [datetime.strptime(d.replace('/', '.').replace('-', '.'), "%d.%m.%Y") for d in date_matches]
                        parsed_dates.sort()
                        if len(parsed_dates) >= 2:
                            offer.dates = f"{parsed_dates[0].strftime('%d.%m.%Y')} - {parsed_dates[-1].strftime('%d.%m.%Y')}"
                        else:
                            offer.dates = parsed_dates[0].strftime('%d.%m.%Y')
                    except:
                        offer.dates = date_matches[0]

            # Extract destination from title or card content
            offer.destination = self._extract_destination_from_title(offer.title, card_text)

            # Only add if we have basic information and it's not a navigation/menu item
            if (offer.title and offer.link and
                len(offer.title) > 15 and  # Longer minimum title length
                not any(skip in offer.title.lower() for skip in [
                    'calendar', 'kalendar', 'news', 'novini', 'contact', 'kontakti',
                    'about', 'za nas', 'services', 'uslugi', 'facebook', 'instagram',
                    'последвайте ни', 'дари тур', 'обслужване', 'контакти',
                    'галерия', 'снимки', 'print', 'карта', 'видео', 'видео галерия',
                    'дати:', '14 дни', '11 нощувки', 'галерия снимки', 'програма',
                    'хотели', 'транспорт', 'информация', 'условия', 'регистрация'
                ]) and
                # Must have at least a price or dates to be considered a real offer
                (offer.price or offer.dates)):
                offers.append(offer)

        return offers

    def _is_individual_offer_page(self, url: str) -> bool:
        """Check if URL is for an individual offer page."""
        path = urlparse(url).path.lower()
        return any(pattern in path for pattern in [
            '/ekskurzia-', '/pochivki-', '/tour-', '/trip-'
        ])

    def _extract_single_offer(self, html: str, url: str) -> Optional[DariTourOffer]:
        """Extract offer details from an individual offer page."""
        soup = BeautifulSoup(html, 'html.parser')
        offer = DariTourOffer()
        offer.link = url

        # Extract title from page title or main heading
        if soup.title:
            title_text = soup.title.get_text().strip()
            # Remove site name from title
            if ' | Дари Тур' in title_text:
                title_text = title_text.replace(' | Дари Тур', '')
            offer.title = title_text

        # Extract price
        page_text = soup.get_text()
        price_match = re.search(r'(\d+(?:,\d{3})*(?:\.\d{2})?)\s*лв', page_text)
        if price_match:
            offer.price = price_match.group(0)

        # Extract dates
        date_matches = re.findall(r'\d{1,2}[./-]\d{1,2}[./-]\d{4}', page_text)
        if date_matches:
            if len(date_matches) == 1:
                offer.dates = date_matches[0]
            else:
                # Sort dates and create range
                try:
                    parsed_dates = [datetime.strptime(d.replace('/', '.').replace('-', '.'), "%d.%m.%Y") for d in date_matches]
                    parsed_dates.sort()
                    if len(parsed_dates) >= 2:
                        offer.dates = f"{parsed_dates[0].strftime('%d.%m.%Y')} - {parsed_dates[-1].strftime('%d.%m.%Y')}"
                    else:
                        offer.dates = parsed_dates[0].strftime('%d.%m.%Y')
                except:
                    offer.dates = date_matches[0]

        # Extract destination - use title and page content specific to this offer
        self._current_offer_url = url  # Set current URL for destination extraction
        offer.destination = self._extract_destination_from_title(offer.title, page_text)

        return offer if offer.title else None

    def _extract_destination_from_title(self, title: str, content: str) -> str:
        """Extract destination from title or content."""
        # City/landmark to country mapping
        city_to_country = {
            'Рио де Жанейро': 'Бразилия',
            'РИО ДЕ ЖАНЕЙРО': 'Бразилия',
            'Виена': 'Австрия',
            'Будапеща': 'Унгария',
            'Прага': 'Чехия',
            'Братислава': 'Словакия',
            'Белград': 'Сърбия',
            'Луковска баня': 'България',
            'Пролом баня': 'България',
            'Върнячка баня': 'България',
            'Кайро': 'Египет',
            'Хургада': 'Египет',
            'Нил': 'Египет',
            'Банкок': 'Тайланд',
            'Москва': 'Русия',
            'Санкт Петербург': 'Русия',
            'Бали': 'Индонезия',
            'Дубай': 'ОАЕ',
        }

        known_destinations = [
            'Китай', 'Ботсвана', 'Коста Рика', 'Узбекистан', 'Мексико', 'Малайзия',
            'Исландия', 'Панама', 'Колумбия', 'Кипър', 'Октомври', 'Непал', 'Патагония',
            'Австралия', 'Нова Зеландия', 'Сингапур', 'Банкок', 'Тайланд',
            'Бразилия', 'Рио де Жанейро', 'Дубай', 'ОАЕ', 'Индия', 'Португалия',
            'Русия', 'Москва', 'Санкт Петербург', 'Доминикана', 'Куба',
            'Япония', 'Виетнам', 'Филипини', 'Индонезия', 'Бали',
            'Южна Корея', 'Тайван', 'Израел', 'Йордания', 'Ливан', 'Турция',
            'Гърция', 'Италия', 'Испания', 'Франция', 'Германия', 'Австрия',
            'Швейцария', 'Чехия', 'Полша', 'Унгария', 'Румъния', 'България',
            'Сърбия', 'Хърватия', 'Словения', 'Черна гора', 'Албания', 'Македония',
            'Великобритания', 'Ирландия', 'Нидерландия', 'Белгия', 'Швеция',
            'Норвегия', 'Дания', 'Финландия', 'Естония', 'Латвия', 'Литва',
            'САЩ', 'Канада', 'Аржентина', 'Чили', 'Перу', 'Еквадор',
            'Боливия', 'Уругвай', 'Парагвай', 'Мароко', 'Тунис', 'Египет',
            'Кения', 'Танзания', 'ЮАР', 'Намибия', 'Замбия', 'Зимбабве', 'Малави',
            'Мозамбик', 'Мадагаскар', 'Сейшелски острови', 'Мавриций', 'Реюнион',
            'Виена', 'Будапеща', 'Прага', 'Братислава', 'Белград', 'Луковска баня',
            'Пролом баня', 'Върнячка баня', 'Кайро', 'Хургада', 'Нил'
        ]

        # Clean title from extra text
        clean_title = title.replace(' ≫ Цени и оферти от България', '').replace(' • Цени със самолет', '')

        # First priority: extract from title using patterns
        title_patterns = [
            r'до\s+([А-ЯA-Z][а-яА-Яa-zA-Z\s]+)',
            r'в\s+([А-ЯA-Z][а-яА-Яa-zA-Z\s]+)',
            r'([А-ЯA-Z][а-яА-Яa-zA-Z\s]+)\s*-\s*екскурзии',
            r'([А-ЯA-Z][а-яА-Яa-zA-Z\s]+)\s*-\s*почивки',
            r'Екскурзии\s+([А-ЯA-Z][а-яА-Яa-zA-Z\s]+)',
            r'Почивки\s+([А-ЯA-Z][а-яА-Яa-zA-Z\s]+)',
            r'([А-ЯA-Z][а-яА-Яa-zA-Z\s]+)\s*и\s+([А-ЯA-Z][а-яА-Яa-zA-Z\s]+)',
            r'([А-ЯA-Z][а-яА-Яa-zA-Z\s]+)\s*круиз',
            r'Круиз\s+([А-ЯA-Z][а-яА-Яa-zA-Z\s]+)',
            r'Коледа\s*-\s*([А-ЯA-Z][а-яА-Яa-zA-Z\s]+)',  # Christmas tours
            r'([А-ЯA-Z][а-яА-Яa-zA-Z\s]+)\s*-\s*([А-ЯA-Z][а-яА-Яa-zA-Z\s]+)',  # City - City
            r'([А-ЯA-Z][а-яА-Яa-zA-Z\s]+)\s*\|\s*([А-ЯA-Z][а-яА-Яa-zA-Z\s]+)',  # City | City
        ]

        for pattern in title_patterns:
            match = re.search(pattern, clean_title, re.IGNORECASE)
            if match:
                potential_dest = match.group(1).strip()
                if potential_dest in known_destinations:
                    # Map cities/landmarks to countries if needed
                    return city_to_country.get(potential_dest, potential_dest)

        # Second priority: extract from URL path
        try:
            from urllib.parse import urlparse
            # For the offer link, extract destination from URL path
            if hasattr(self, '_current_offer_url'):
                parsed_url = urlparse(self._current_offer_url)
            else:
                parsed_url = urlparse(title if title.startswith('http') else f"http://dummy.com{title}")
            path_parts = parsed_url.path.split('/')
            for part in path_parts:
                if part and len(part) > 2:
                    # Handle specific URL patterns
                    if 'nepal' in part:
                        return 'Непал'
                    elif 'bali' in part:
                        return 'Бали'
                    elif 'dominikan' in part:
                        return 'Доминикана'
                    elif 'brazil' in part:
                        return 'Бразилия'
                    elif 'patagoniya' in part or 'patagonia' in part:
                        return 'Патагония'
                    elif 'surbiya' in part or 'serbia' in part or 'belgrad' in part:
                        return 'Сърбия'
                    elif 'singapur' in part or 'singapore' in part:
                        return 'Сингапур'
                    elif 'kipur' in part or 'cyprus' in part:
                        return 'Кипър'
                    elif 'nil' in part or 'kayro' in part or 'hurgada' in part:
                        return 'Египет'
                    elif 'viena' in part or 'budapeshta' in part or 'praga' in part or 'bratislava' in part:
                        return 'Австрия'  # Default to Austria for Central European tours
                    elif 'lukovska-banya' in part or 'prolom-banya' in part or 'vurnyachka-banya' in part:
                        return 'България'
                    # General case
                    decoded_part = part.replace('-', ' ').title()
                    if decoded_part in known_destinations:
                        return city_to_country.get(decoded_part, decoded_part)
        except:
            pass

        # Third priority: direct match in title
        title_upper = clean_title.upper()
        for dest in known_destinations:
            if dest.upper() in title_upper:
                return city_to_country.get(dest, dest)

        # Fourth priority: look for destination in content but limit to avoid other offers
        # Only check the beginning of content (first 500 chars) to avoid picking up other offers
        content_start = content[:500]
        text_to_check = f"{clean_title} {content_start}".upper()

        # Find all matching destinations
        matches = []
        for dest in known_destinations:
            if dest.upper() in text_to_check:
                matches.append(dest)

        if matches:
            # Return the first match
            return matches[0]

        return ""

    async def scrape_main_page(self) -> List[DariTourOffer]:
        """Scrape offers from the main page."""
        print("=== Scraping Dari Tour main page ===")

        html = await self.fetch_page(self.BASE_URL)
        if not html:
            return []

        offers = self.extract_offers_from_page(html, self.BASE_URL)
        print(f"✓ Found {len(offers)} offers on main page")
        return offers

    async def scrape_category_pages(self) -> List[DariTourOffer]:
        """Scrape offers from category pages."""
        print("=== Scraping Dari Tour category pages ===")

        category_urls = [
            "https://dari-tour.com/ekskurzii",
            "https://dari-tour.com/top-oferti",
            "https://dari-tour.com/pochivki",
        ]

        all_offers = []

        for url in category_urls:
            print(f"Scraping category: {url}")
            html = await self.fetch_page(url)
            if html:
                offers = self.extract_offers_from_page(html, url)
                all_offers.extend(offers)
                print(f"✓ Found {len(offers)} offers in {url}")

                # Rate limiting
                await asyncio.sleep(1)

        return all_offers

    async def scrape_individual_offers(self, offer_urls: List[str]) -> List[DariTourOffer]:
        """Scrape detailed information from individual offer pages."""
        print(f"=== Scraping {len(offer_urls)} individual offer pages ===")

        offers = []

        for i, url in enumerate(offer_urls, 1):
            if i % 5 == 0:
                print(f"Processed {i}/{len(offer_urls)} offers...")

            if url in self.processed_urls:
                continue

            html = await self.fetch_page(url)
            if html:
                self.processed_urls.add(url)
                # Extract all offers from this page (some pages contain multiple offers)
                page_offers = self.extract_offers_from_page(html, url)
                offers.extend(page_offers)

            # Rate limiting
            await asyncio.sleep(0.5)

        print(f"✓ Extracted details from {len(offers)} individual offers")
        return offers

    async def scrape_all_offers(self, limit: Optional[int] = None) -> List[DariTourOffer]:
        """Scrape all offers from Dari Tour."""
        print("=== DARI TOUR SCRAPER ===")

        all_offers = []

        # First, scrape offers directly from main page and category pages
        print("=== Scraping main page and category pages ===")

        # Scrape main page
        main_html = await self.fetch_page(self.BASE_URL)
        if main_html:
            main_offers = self.extract_offers_from_page(main_html, self.BASE_URL)
            all_offers.extend(main_offers)
            print(f"✓ Fetched: {self.BASE_URL} ({len(main_html)} chars)")

        # Scrape general category pages
        category_pages = ["https://dari-tour.com/ekskurzii", "https://dari-tour.com/top-oferti"]
        for cat_url in category_pages:
            cat_html = await self.fetch_page(cat_url)
            if cat_html:
                cat_offers = self.extract_offers_from_page(cat_html, cat_url)
                all_offers.extend(cat_offers)
                print(f"✓ Fetched: {cat_url} ({len(cat_html)} chars)")

        # Scrape destination-specific category pages that contain multiple offers
        destination_category_pages = [
            "https://dari-tour.com/pochivki-dominikanska-republika",
            "https://dari-tour.com/pochivki-meksiko",
            "https://dari-tour.com/pochivki-ispaniya",
            "https://dari-tour.com/pochivki-italiya",
            "https://dari-tour.com/pochivki-turtsiya",
            "https://dari-tour.com/pochivki-egipet",
            "https://dari-tour.com/pochivki-tunis",
            "https://dari-tour.com/pochivki-gretsiya",
            "https://dari-tour.com/ekskurzii-sasht",
            "https://dari-tour.com/ekskurzii-evropa",
            "https://dari-tour.com/ekskurzii-aziq",
        ]

        print(f"\n=== Scraping {len(destination_category_pages)} destination category pages ===")
        for dest_url in destination_category_pages:
            dest_html = await self.fetch_page(dest_url)
            if dest_html:
                dest_offers = self.extract_offers_from_page(dest_html, dest_url)
                all_offers.extend(dest_offers)
                print(f"✓ Found {len(dest_offers)} offers in {dest_url}")

        # Now scrape individual offer URLs
        all_offer_urls = set()

        # Get offer URLs from main page
        if main_html:
            main_urls = self.extract_offer_links(main_html)
            all_offer_urls.update(main_urls)

        # Get offer URLs from category pages
        for cat_url in category_pages:
            cat_html = await self.fetch_page(cat_url)
            if cat_html:
                cat_urls = self.extract_offer_links(cat_html)
                all_offer_urls.update(cat_urls)

        offer_urls_list = list(all_offer_urls)
        if limit:
            offer_urls_list = offer_urls_list[:limit]
            print(f"Limited to {limit} offers for testing")

        print(f"Found {len(offer_urls_list)} offer URLs to process")

        # Scrape individual offer pages
        individual_offers = await self.scrape_individual_offers(offer_urls_list)
        all_offers.extend(individual_offers)

        # Remove duplicates based on title + link combination
        seen = set()
        unique_offers = []
        for offer in all_offers:
            key = (offer.title, offer.link)
            if key not in seen:
                seen.add(key)
                unique_offers.append(offer)

        print(f"✓ Removed {len(all_offers) - len(unique_offers)} duplicate offers")

        self.scraped_offers = unique_offers
        print(f"\n✓ Total unique offers scraped: {len(unique_offers)}")
        return unique_offers

    async def save_results(self):
        """Save scraped data to JSON file with only required fields."""
        output_path = "/home/dani/Desktop/Organizer/travel-comparator/dari_tour_scraped.json"

        # Save JSON with only required fields
        offers_data = [
            {
                "title": offer.title,
                "link": offer.link,
                "price": offer.price,
                "dates": offer.dates,
                "destination": offer.destination
            }
            for offer in self.scraped_offers
        ]

        async with aiofiles.open(output_path, 'w', encoding='utf-8') as f:
            await f.write(json.dumps(offers_data, ensure_ascii=False, indent=2))

        print(f"✓ Exported to JSON: {output_path}")


async def main():
    """Main scraping function."""
    limit = None
    debug_urls = []

    if len(sys.argv) > 1:
        try:
            # Parse arguments - can be limit, URLs, or mixed
            for arg in sys.argv[1:]:
                if arg.isdigit():
                    limit = int(arg)
                    print(f"Limiting to {limit} offers for testing")
                elif arg.startswith('http'):
                    debug_urls.append(arg)
                else:
                    print(f"Unknown argument: {arg}")
                    print("Usage: python dari_tour_scraper.py [limit] [url1] [url2] ...")
                    print("Examples:")
                    print("  python dari_tour_scraper.py 5                    # Limit to 5 offers")
                    print("  python dari_tour_scraper.py https://...          # Test single offer")
                    print("  python dari_tour_scraper.py https://... https://...  # Test multiple offers")
                    return

            if debug_urls:
                print(f"Debug URLs: {len(debug_urls)}")
                for url in debug_urls:
                    print(f"  - {url}")

        except ValueError:
            print("Usage: python dari_tour_scraper.py [limit] [url1] [url2] ...")
            return

    async with DariTourScraper() as scraper:
        if debug_urls:
            # Debug multiple URLs mode
            print(f"\n=== DEBUG MODE: Testing {len(debug_urls)} URLs ===")

            all_debug_offers = []

            for i, debug_url in enumerate(debug_urls, 1):
                print(f"\n[{i}/{len(debug_urls)}] Processing: {debug_url}")

                html = await scraper.fetch_page(debug_url)
                if html:
                    offers = scraper.extract_offers_from_page(html, debug_url)
                    print(f"Found {len(offers)} offers on the page")

                    # Filter out non-travel offers (navigation, etc.)
                    valid_offers = []
                    for offer in offers:
                        # Skip offers that look like navigation/menu items
                        if (offer.title and len(offer.title) > 15 and
                            not any(skip in offer.title.lower() for skip in [
                                'calendar', 'kalendar', 'news', 'novini', 'contact', 'kontakti',
                                'about', 'za nas', 'services', 'uslugi', 'facebook', 'instagram',
                                'последвайте ни', 'дари тур', 'обслужване', 'контакти',
                                'галерия', 'снимки', 'print', 'карта', 'видео', 'видео галерия',
                                'дати:', '14 дни', '11 нощувки', 'галерия снимки', 'програма',
                                'хотели', 'транспорт', 'информация', 'условия', 'регистрация'
                            ]) and
                            # Must have at least a price or dates to be considered a real offer
                            (offer.price or offer.dates)):
                            valid_offers.append(offer)

                    print(f"Valid travel offers: {len(valid_offers)}")
                    all_debug_offers.extend(valid_offers)

                    # Show sample offers
                    for j, offer in enumerate(valid_offers[:3]):
                        print(f"  {j+1}. {offer.title[:60]}... - {offer.destination} - {offer.price}")

            # Export all debug results to JSON
            output_data = [offer.to_dict() for offer in all_debug_offers]
            with open('dari_tour_debug.json', 'w', encoding='utf-8') as f:
                json.dump(output_data, f, ensure_ascii=False, indent=2)
            print(f"\n✓ Exported {len(all_debug_offers)} debug offers to JSON: dari_tour_debug.json")

            print(f"Debug complete for {len(debug_urls)} URLs")
        else:
            # Normal scraping mode
            offers = await scraper.scrape_all_offers(limit=limit)
            if offers:
                await scraper.save_results()

            print("\n=== SCRAPE COMPLETE ===")
            print(f"Total offers: {len(offers)}")


if __name__ == "__main__":
    import sys
    asyncio.run(main())