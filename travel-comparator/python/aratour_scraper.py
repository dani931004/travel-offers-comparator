#!/usr/bin/env python3
"""
Aratour Scraper - Comprehensive scraper for aratour.bg

This scraper extracts travel offers from Aratour, a Bulgarian travel agency.
Unlike Dari Tour which displays offers directly, Aratour organizes offers by destination
and provides detailed hotel options for each offer.

Features:
- Discovers all destinations from main page
- Extracts offers from destination pages
- Parses offer details, prices, and hotel options
- Handles Bulgarian language content
- Outputs structured JSON and CSV data
"""

import asyncio
import json
import re
import csv
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional, Set, Any
from dataclasses import dataclass, field

import aiohttp
import aiofiles
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse, unquote


@dataclass
class AratourOffer:
    """Data structure for Aratour offers with basic information."""
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


class AratourScraper:
    """Scraper for Aratour travel offers."""

    BASE_URL = "https://aratour.bg"
    OUTPUT_DIR = Path(__file__).parent / "output"

    def __init__(self):
        self.session: Optional[aiohttp.ClientSession] = None
        self.scraped_offers: List[AratourOffer] = []
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

    def extract_destinations(self, html: str) -> List[Dict[str, str]]:
        """Extract destination URLs from main page."""
        soup = BeautifulSoup(html, 'html.parser')
        destinations = []
        found_urls = set()

        # Find all destination links (both excursions and holidays)
        # Look for links containing "екскурзии" (excursions) or "pochivki" (holidays)
        dest_patterns = [
            r'href="([^"]*екскурзии[^"]*)"',  # Excursion destinations
            r'href="([^"]*pochivki[^"]*)"',   # Holiday destinations
            r'href="([^"]*оферти[^"]*)"',     # Promotional offers pages
        ]

        for pattern in dest_patterns:
            matches = re.findall(pattern, html, re.IGNORECASE)
            for match in matches:
                if match.startswith('/'):
                    full_url = urljoin(self.BASE_URL, match)
                elif match.startswith('http'):
                    full_url = match
                else:
                    # Handle relative URLs that don't start with /
                    full_url = urljoin(self.BASE_URL + '/', match)

                if full_url not in found_urls and full_url != self.BASE_URL:
                    found_urls.add(full_url)

                    # Skip non-destination pages (partnerships, special offers, etc.)
                    path_lower = urlparse(full_url).path.lower()
                    skip_keywords = [
                        'партньорство', 'partnership', 'абакс', 'abaks',
                        'ранни-записвания', 'early-booking', 'коледа', 'christmas',
                        'нова-година', 'new-year', 'великден', 'easter',
                        'лято', 'summer', 'зима', 'winter', 'пролет', 'spring', 'есен', 'autumn',
                        'уикенд', 'weekend', 'екзотични', 'exotic', 'круизи', 'cruises',
                        'авторски', 'author', 'специални', 'special', 'промо', 'promo'
                    ]
                    
                    should_skip = any(keyword in path_lower for keyword in skip_keywords)
                    if should_skip:
                        continue

                    # Extract destination name from URL or link text
                    path = urlparse(full_url).path
                    name = path.split('/')[-2] if len(path.split('/')) > 2 else path.split('/')[-1]
                    name = name.replace('-', ' ').title()

                    # Try to get better name from link text
                    link_elem = soup.find('a', href=match)
                    if link_elem:
                        text = link_elem.get_text().strip()
                        if text and len(text) > 2 and not text.startswith('http'):
                            name = text

                    destinations.append({
                        'url': full_url,
                        'name': name,
                        'type': 'excursions' if 'екскурзии' in full_url else 'holidays'
                    })

        # Remove duplicates based on URL
        unique_destinations = []
        seen_urls = set()
        for dest in destinations:
            if dest['url'] not in seen_urls:
                seen_urls.add(dest['url'])
                unique_destinations.append(dest)

        return unique_destinations

    def extract_offers_from_page(self, html: str, destination_url: str) -> List[AratourOffer]:
        """Extract offers from a destination page."""
        soup = BeautifulSoup(html, 'html.parser')
        offers = []

        # Extract destination name from URL
        path = urlparse(destination_url).path
        destination_name = path.split('/')[-2] if len(path.split('/')) > 2 else path.split('/')[-1]
        destination_name = destination_name.replace('-', ' ').title()

        # Look for offer cards - Aratour uses different structures
        # Try multiple selectors for offer containers
        offer_selectors = [
            'div.offer-card',
            'div.offer-item',
            'div.tour-item',
            'article.offer',
            '.offer-listing',
            '.tour-offer'
        ]

        offer_cards = []
        for selector in offer_selectors:
            cards = soup.select(selector)
            if cards:
                offer_cards.extend(cards)
                break

        # If no specific selectors work, look for links containing offer info
        if not offer_cards:
            offer_links = soup.find_all('a', href=re.compile(r'pochi|tour|\d{3,}'))
            for link in offer_links:
                # Check if parent contains price information
                parent = link.parent
                if parent and re.search(r'\d+\s*(лв|€|\$)', parent.get_text()):
                    offer_cards.append(parent)

        for card in offer_cards:
            card_text = card.get_text().strip()

            # Skip non-offer content
            skip_keywords = ['Календар', 'Новини', 'Бюлетин', 'Aratour', 'Контакти', 'Карта на сайта']
            if any(keyword in card_text for keyword in skip_keywords):
                continue

            # Skip if it doesn't contain price information
            if not re.search(r'\d+\s*(лв\.?|€|\$|USD)', card_text):
                continue

            offer = AratourOffer()
            offer.destination = destination_name

            # Extract individual offer URL
            offer_link = card.find('a')
            if offer_link and offer_link.get('href'):
                href = offer_link.get('href').strip()
                if href.startswith('/'):
                    offer.link = urljoin(self.BASE_URL, href)
                elif href.startswith('http'):
                    offer.link = href
                else:
                    offer.link = urljoin(self.BASE_URL + '/', href)
            else:
                # Fallback to destination URL if no individual link found
                offer.link = destination_url

            # Extract title
            title_elem = card.find(['h1', 'h2', 'h3', 'h4', 'strong', 'b'])
            if title_elem:
                title_text = title_elem.get_text().strip()
                if title_text not in ['Aratour', ''] and len(title_text) > 10:
                    offer.title = title_text
                else:
                    # Extract first meaningful line
                    lines = [line.strip() for line in card_text.split('\n') if line.strip() and len(line.strip()) > 10]
                    if lines:
                        offer.title = lines[0][:150]
            else:
                # Extract first meaningful line as title
                lines = [line.strip() for line in card_text.split('\n') if line.strip() and len(line.strip()) > 10]
                if lines:
                    offer.title = lines[0][:150]

            # Extract price
            price_pattern = re.compile(r'(\d+(?:\s+\d+)*[.,]?\d*)\s*(лв\.?|€|\$|USD)')
            price_match = price_pattern.search(card_text)
            if price_match:
                offer.price = price_match.group(0)

            # Extract dates
            date_patterns = [
                r'(\d{1,2}[./-]\d{1,2}[./-]\d{4})\s*-\s*(\d{1,2}[./-]\d{1,2}[./-]\d{4})',
                r'Дати на пътуване:\s*([^<\n]+)',
                r'(\d{1,2}[./-]\d{1,2}[./-]\d{4})',
            ]
            for pattern in date_patterns:
                match = re.search(pattern, card_text, re.IGNORECASE)
                if match:
                    if len(match.groups()) == 2:
                        offer.dates = f"{match.group(1)} - {match.group(2)}"
                    else:
                        offer.dates = match.group(1)
                    break

            # Extract duration (days)
            duration_pattern = re.compile(r'(\d+)\s*дни')
            duration_match = duration_pattern.search(card_text)
            if duration_match:
                offer.duration = duration_match.group(0)

            # Extract description
            description_parts = []
            lines = [line.strip() for line in card_text.split('\n') if line.strip()]

            for line in lines:
                # Skip the title line
                if offer.title and line.startswith(offer.title[:50]):
                    continue
                # Skip price lines
                if offer.price and offer.price in line:
                    continue
                # Skip duration lines
                if offer.duration and offer.duration in line:
                    continue
                # Skip very short lines or navigation elements
                if len(line) > 5 and not any(nav in line for nav in ['Aratour', 'Контакти', 'Карта']):
                    description_parts.append(line)

            offer.description = ' '.join(description_parts)[:500]

            # Only add if we have a meaningful title and price
            if offer.title and offer.price and len(offer.title) > 10:
                offers.append(offer)

        # If no structured offers found, try extracting from main page offers
        if not offers:
            offers = self.extract_offers_from_main_page(html, destination_url)

        return offers

    def extract_offers_from_main_page(self, html: str, base_url: str) -> List[AratourOffer]:
        """Extract offers directly from main page or destination listings."""
        soup = BeautifulSoup(html, 'html.parser')
        offers = []

        # Look for offer links with prices - expanded patterns for main page
        offer_patterns = [
            r'pochi|tour|\d{4,}',  # Original pattern
            r'екскурзия|почивка',  # Bulgarian terms
            r'offer|travel|trip',  # English terms
        ]
        offer_links = []
        for pattern in offer_patterns:
            links = soup.find_all('a', href=re.compile(pattern, re.IGNORECASE))
            offer_links.extend(links)

        # Remove duplicates
        seen_hrefs = set()
        unique_offer_links = []
        for link in offer_links:
            href = link.get('href')
            if href and href not in seen_hrefs:
                seen_hrefs.add(href)
                unique_offer_links.append(link)

        # Also look for offers in special sections (featured offers, promotions, etc.)
        special_sections = soup.find_all(['div', 'section'], class_=re.compile(r'offer|promo|featured|special|highlight', re.IGNORECASE))
        for section in special_sections:
            section_links = section.find_all('a', href=True)
            for link in section_links:
                href = link.get('href')
                if href and href not in seen_hrefs:
                    # Check if this looks like an offer link
                    if any(keyword in href.lower() for keyword in ['екскурзия', 'почивка', 'tour', 'pochi']):
                        seen_hrefs.add(href)
                        unique_offer_links.append(link)

        for link in unique_offer_links:
            href = link.get('href')
            if not href:
                continue

            # Get the full text of the link and its surrounding context
            context = link.parent.get_text() if link.parent else link.get_text()

            offer = AratourOffer()

            # Set link
            if href.startswith('/'):
                offer.link = urljoin(self.BASE_URL, href)
            elif href.startswith('http'):
                offer.link = href
            else:
                # Handle relative URLs that don't start with /
                offer.link = urljoin(self.BASE_URL + '/', href)

            print(f"Full link: {offer.link}")

            # Filter out tracking URLs and non-offer links
            parsed_url = urlparse(offer.link)
            query_params = parsed_url.query

            # Skip if URL contains tracking parameters
            tracking_params = ['gclid', 'gad_source', 'gad_campaignid', 'utm_', 'fbclid', 'msclkid']
            if any(param in query_params for param in tracking_params):
                continue

            # Skip destination page links - these are scraped separately as destinations
            # Only skip if it's clearly a destination overview page (ends with just a number)
            path = parsed_url.path.lower()
            # URL decode the path to handle Cyrillic characters
            try:
                decoded_path = unquote(path)
            except:
                decoded_path = path

            # Skip destination overview pages: /почивки/destination/number or /екскурзии/destination/number
            # But allow individual offers: /екскурзия/offer-name/id or /почивка/offer-name/id
            skip_destination = False

            if (decoded_path.startswith('/почивки/') or decoded_path.startswith('/екскурзии/')):
                path_parts = decoded_path.split('/')
                # If it has the form /почивки/destination/id or /екскурзии/destination/id, it's likely a destination page
                if len(path_parts) == 4 and path_parts[-1].isdigit():
                    skip_destination = True
            elif 'pochivki-' in decoded_path or 'екскурзии-' in decoded_path:
                # URLs like /pochivki-malta or /екскурзии-italy are destination pages
                skip_destination = True
            elif decoded_path.startswith('/оферти/'):
                # URLs like /оферти/ранни-записвания-турция-2025/24 are promotional pages with multiple offers
                skip_destination = True

            if skip_destination:
                continue

            # For main page, be more lenient with URL filtering
            if base_url == self.BASE_URL:
                # On main page, allow various types of links that might be offers
                path = parsed_url.path.lower()
                # Skip obvious non-offers
                skip_paths = ['/contacts', '/about', '/terms', '/privacy', '/sitemap', '/news', '/newsletter']
                if any(skip_path in path for skip_path in skip_paths):
                    continue
            else:
                # For destination pages, be stricter
                path = parsed_url.path.lower()
                if not any(keyword in path for keyword in ['pochi', 'екскурзия', 'tour', 'пътуван']):
                    if path not in ['', '/'] and not path.startswith('/екскурзии') and not path.startswith('/почивки'):
                        continue

            # Skip if link text looks like navigation or non-offer content
            link_text = link.get_text().strip().lower()
            skip_keywords = ['телефон', 'имейл', 'контакт', 'за нас', 'условия', 'политика', 'карта', 'булетин', 'новини', 'facebook', 'instagram', '0999', '@']
            if any(keyword in link_text for keyword in skip_keywords):
                continue

            # Skip social media and contact links
            if 'facebook.com' in offer.link or 'instagram.com' in offer.link or 'mailto:' in offer.link or 'tel:' in offer.link:
                continue

            # Skip informational pages that are not actual offers
            path = parsed_url.path.lower()
            if any(info_pattern in path for info_pattern in ['колко-струва', '~']):
                continue

            print(f"Link passed all filters, processing offer details")

            # For main page offers, be more lenient - don't require price in immediate context
            if base_url == self.BASE_URL:
                # On main page, we'll extract details later from the individual offer page
                pass
            else:
                # Check if it contains price information
                if not re.search(r'\d+\s*(лв\.?|€|\$|USD)', context):
                    continue

            # Extract title from link text or context - be more lenient for main page
            title = link.get_text().strip()
            if base_url == self.BASE_URL:
                # For main page, accept shorter titles
                if title and len(title) > 3:
                    offer.title = title[:150]
                else:
                    # Try to extract from context or use URL path as fallback
                    lines = [line.strip() for line in context.split('\n') if line.strip() and len(line.strip()) > 3]
                    if lines:
                        offer.title = lines[0][:150]
                    else:
                        # Use URL path as title fallback
                        path_parts = urlparse(offer.link).path.split('/')
                        if len(path_parts) > 1:
                            title_from_url = path_parts[-2] if path_parts[-1].isdigit() else path_parts[-1]
                            offer.title = title_from_url.replace('-', ' ').title()[:150]
            else:
                # For destination pages, require longer titles
                if title and len(title) > 10:
                    offer.title = title[:150]
                else:
                    # Try to extract from context
                    lines = [line.strip() for line in context.split('\n') if line.strip() and len(line.strip()) > 10]
                    if lines:
                        offer.title = lines[0][:150]

            # Extract price - be more lenient for main page
            price_pattern = re.compile(r'(\d+(?:,\d+)?)\s*(лв\.?|€|\$|USD)')
            price_match = price_pattern.search(context)
            if price_match:
                offer.price = price_match.group(0)
            elif base_url == self.BASE_URL:
                # For main page offers, we'll get price from individual page later
                offer.price = "Цена по запитване"  # Price on request

            # Extract duration
            duration_pattern = re.compile(r'(\d+)\s*дни')
            duration_match = duration_pattern.search(context)
            if duration_match:
                offer.duration = duration_match.group(0)

            # Extract description from remaining context
            description_parts = []
            lines = [line.strip() for line in context.split('\n') if line.strip()]

            for line in lines:
                if offer.title and line.startswith(offer.title[:50]):
                    continue
                if offer.price and offer.price in line:
                    continue
                if offer.duration and offer.duration in line:
                    continue
                if len(line) > 5:
                    description_parts.append(line)

            offer.description = ' '.join(description_parts)[:500]

            # For main page offers, require at least a title
            if base_url == self.BASE_URL:
                if offer.title and len(offer.title) > 2:
                    offers.append(offer)
                    print(f"Added main page offer: {offer.title[:50]}...")
            else:
                if offer.title and offer.price:
                    offers.append(offer)

        return offers

    async def scrape_destination(self, destination: Dict[str, str]) -> List[AratourOffer]:
        """Scrape all offers from a destination page."""
        url = destination['url']
        name = destination['name']

        print(f"\n=== Scraping destination: {name} ===")
        print(f"URL: {url}")

        if url in self.processed_urls:
            print(f"✓ Already processed: {url}")
            return []

        html = await self.fetch_page(url)
        if not html:
            return []

        self.processed_urls.add(url)
        offers = self.extract_offers_from_page(html, url)

        print(f"✓ Found {len(offers)} offers in {name}")
        return offers

    async def scrape_main_page_offers(self) -> List[AratourOffer]:
        """Scrape offers directly from the main page."""
        print("=== Scraping main page offers ===")

        html = await self.fetch_page(self.BASE_URL)
        if not html:
            return []

        offers = self.extract_offers_from_main_page(html, self.BASE_URL)
        print(f"✓ Found {len(offers)} offers on main page")
        return offers

    async def scrape_all_destinations(self, limit: Optional[int] = None) -> List[AratourOffer]:
        """Scrape offers from all destinations."""
        print("=== ARATOUR SCRAPER ===")
        print("Discovering destinations...")

        # Fetch main page
        main_html = await self.fetch_page(self.BASE_URL)
        if not main_html:
            print("Failed to fetch main page")
            return []

        # Extract destinations
        destinations = self.extract_destinations(main_html)
        print(f"Found {len(destinations)} destinations")

        # Also get offers from main page
        all_offers = await self.scrape_main_page_offers()

        if limit:
            destinations = destinations[:limit]
            print(f"Limited to {limit} destinations for testing")

        # Scrape each destination
        for i, dest in enumerate(destinations, 1):
            print(f"\n[{i}/{len(destinations)}] Processing {dest['name']}")
            offers = await self.scrape_destination(dest)
            all_offers.extend(offers)

            # Rate limiting
            if i < len(destinations):
                await asyncio.sleep(1)

        # Extract detailed information from individual offer pages
        print(f"\nExtracting detailed information from {len(all_offers)} offers...")
        for i, offer in enumerate(all_offers, 1):
            if i % 10 == 0:
                print(f"Processed {i}/{len(all_offers)} offers...")

            # Check if this is an offer that needs detailed extraction
            # Handle both regular and URL-encoded versions
            if offer.link:
                decoded_link = offer.link.lower()
                # URL decode the entire link to handle Cyrillic characters
                try:
                    decoded_link = unquote(decoded_link)
                except:
                    pass  # If decoding fails, use original

                if ('pochi' in decoded_link or 'екскурзия' in decoded_link or 'почивка' in decoded_link or
                    'пътуван' in decoded_link or '/tour' in decoded_link):
                    await self.extract_offer_details(offer)
                else:
                    # For main page offers, check if they look like destination links
                    path_parts = urlparse(offer.link).path.lower().split('/')
                    if len(path_parts) >= 3 and path_parts[-2] in ['екскурзии', 'почивки', 'tours', 'vacations']:
                        await self.extract_offer_details(offer)

            # Rate limiting for detail extraction
            await asyncio.sleep(0.5)

        self.scraped_offers = all_offers
        print(f"\n✓ Total offers scraped: {len(all_offers)}")
        return all_offers

    async def save_results(self):
        """Save scraped data to JSON file with only required fields."""
        output_path = "/home/dani/Desktop/Organizer/aratur.json"

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

    async def extract_offer_details(self, offer: AratourOffer) -> None:
        """
        Extract detailed information from an individual offer page.

        Updates the offer object with program_info, price_includes, price_excludes,
        hotel_titles, booking_conditions, and hotel_options.
        """
        try:
            html = await self.fetch_page(offer.link)
            if not html:
                return

            # Save debug HTML if in debug mode
            if hasattr(self, '_debug_mode') and self._debug_mode:
                debug_dir = Path("dev")
                debug_dir.mkdir(exist_ok=True)
                debug_file = debug_dir / f"debug_offer_{offer.link.split('/')[-1]}.html"
                async with aiofiles.open(debug_file, 'w', encoding='utf-8') as f:
                    await f.write(html)
                print(f"✓ Saved debug HTML: {debug_file}")

            await self._extract_offer_details_with_html(offer, html)
        except Exception as e:
            print(f"✗ Error extracting details for {offer.link}: {e}")

    async def _extract_offer_details_with_html(self, offer: AratourOffer, html: str) -> None:
        """
        Extract destination information from HTML content.
        """
        soup = BeautifulSoup(html, 'html.parser')

        # Clean HTML for better parsing
        for script in soup(["script", "style"]):
            script.decompose()

        # Extract destination from the offer page if not already set properly
        known_destinations = [
            'Турция', 'Гърция', 'Италия', 'Испания', 'Франция', 'Египет',
            'Тунис', 'Мароко', 'България', 'Албания', 'Македония', 'Сърбия',
            'Черна гора', 'Хърватия', 'Словения', 'Австрия', 'Швейцария',
            'Чехия', 'Полша', 'Унгария', 'Румъния', 'Германия', 'Холандия',
            'Белгия', 'Великобритания', 'Ирландия', 'Португалия', 'Йордания',
            'Куба', 'Мексико', 'Доминикана', 'Ямайка', 'Тайланд', 'Виетнам',
            'Япония', 'Китай', 'Индия', 'Индонезия', 'Малайзия', 'Сингапур',
            'Южна Корея', 'Филипини', 'Австралия', 'Нова Зеландия', 'Канада',
            'САЩ', 'Бразилия', 'Аржентина', 'Чили', 'Перу', 'Колумбия',
            'Еквадор', 'Боливия', 'Уругвай', 'Парагвай', 'Малта'
        ]

        should_extract_destination = (
            not offer.destination or
            offer.destination == "" or
            offer.destination not in known_destinations or
            any(skip_word in offer.destination.lower() for skip_word in [
                'pochi', 'ekskurzi', 'tour', 'пътуван', 'пътешеств', 'vacation', 'trip',
                'early', 'booking', 'ранни', 'записван', 'лято', 'зима', 'пролет', 'есен',
                'all', 'inclusive', 'all-inclusive', 'всичко', 'включен', 'от', 'до', 'в',
                'партньорство', 'partnership', 'абакс', 'abaks', 'коледа', 'christmas',
                'нова-година', 'new-year', 'великден', 'easter', 'уикенд', 'weekend',
                'екзотични', 'exotic', 'круизи', 'cruises', 'авторски', 'author',
                'специални', 'special', 'промо', 'promo'
            ])
        )

        if should_extract_destination:
            # Try to extract from page title first
            title_elem = soup.find('title')
            if title_elem:
                title_text = title_elem.get_text().strip()
                # Look for destination patterns in title
                destination_patterns = [
                    r'([А-ЯA-Z][а-яА-Яa-zA-Z\s]+)\s+\d{4}\s*–',  # "Малта 2025 –"
                    r'Aratour\s*-\s*([А-ЯA-Z][а-яА-Яa-zA-Z\s]+)',
                    r'Екскурзия\s+до\s+([А-ЯA-Z][а-яА-Яa-zA-Z\s]+)',
                    r'Почивка\s+в\s+([А-ЯA-Z][а-яА-Яa-zA-Z\s]+)',
                    r'([А-ЯA-Z][а-яА-Яa-zA-Z\s]+)\s*-\s*Aratour',
                ]
                for pattern in destination_patterns:
                    match = re.search(pattern, title_text, re.IGNORECASE)
                    if match:
                        extracted_dest = match.group(1).strip()
                        if extracted_dest in known_destinations:
                            offer.destination = extracted_dest
                            return

            # If not found in title, try meta description
            meta_desc = soup.find('meta', attrs={'name': 'description'})
            if meta_desc and meta_desc.get('content'):
                desc_text = meta_desc['content']
                for dest in known_destinations:
                    if dest in desc_text:
                        offer.destination = dest
                        return

            # Final fallback: URL path
            if not offer.destination:
                path = urlparse(offer.link).path
                path_parts = path.split('/')
                for i, part in enumerate(path_parts):
                    if part and len(part) > 2 and not part.isdigit():
                        decoded_part = unquote(part).replace('-', ' ').strip()
                        if decoded_part in known_destinations:
                            offer.destination = decoded_part
                            return

    async def fix_destination_extraction(self, offers: List[AratourOffer]) -> List[AratourOffer]:
        """
        Fix destination extraction for offers that have incorrect destinations.
        Re-extracts destinations for offers with partnership or other invalid destinations.
        """
        fixed_offers = []

        for offer in offers:
            # Check if destination needs fixing
            invalid_destinations = [
                'В Партньорство С Абакс', 'В Партньорство С Абакс'.lower(),
                'партньорство', 'partnership', 'абакс', 'abaks'
            ]
            
            needs_fixing = (
                not offer.destination or
                offer.destination == "" or
                any(invalid in offer.destination.lower() for invalid in invalid_destinations)
            )
            
            if needs_fixing:
                print(f"Fixing destination for offer: {offer.title[:50]}...")
                
                # Fetch the offer page
                html = await self._fetch_page(offer.link)
                if html:
                    # Reset destination and re-extract
                    offer.destination = ""
                    await self._extract_offer_details_with_html(offer, html)
                    print(f"  Fixed destination: '{offer.destination}'")
                else:
                    print(f"  Failed to fetch page for: {offer.link}")
            
            fixed_offers.append(offer)
        
        return fixed_offers


async def main():
    """Main scraping function."""
    limit = None
    debug_urls = []

    if len(sys.argv) > 1:
        try:
            # Parse arguments - can be limit, URLs, or mixed
            for arg in sys.argv[1:]:
                if arg == 'fix':
                    # Fix existing data
                    print("Loading existing data to fix destinations...")
                    try:
                        with open('aratur.json', 'r', encoding='utf-8') as f:
                            data = json.load(f)
                        
                        # Convert dicts back to AratourOffer objects
                        offers = []
                        for item in data:
                            offer = AratourOffer()
                            offer.title = item.get('title', '')
                            offer.link = item.get('link', '')
                            offer.price = item.get('price', '')
                            offer.dates = item.get('dates', '')
                            offer.description = item.get('description', '')
                            offer.destination = item.get('destination', '')
                            offer.duration = item.get('duration', '')
                            offer.program_info = item.get('program_info', '')
                            offer.price_includes = item.get('price_includes', [])
                            offer.price_excludes = item.get('price_excludes', [])
                            offer.hotel_titles = item.get('hotel_titles', [])
                            offer.booking_conditions = item.get('booking_conditions', '')
                            offer.hotel_options = item.get('hotel_options', [])
                            offer.scraped_at = item.get('scraped_at', '')
                            offers.append(offer)
                        
                        print(f"Loaded {len(offers)} offers")
                        
                        # Fix destinations
                        async with AratourScraper() as scraper:
                            fixed_offers = await scraper.fix_destination_extraction(offers)
                        
                        # Save fixed data
                        output_data = [offer.to_dict() for offer in fixed_offers]
                        with open('aratur_fixed.json', 'w', encoding='utf-8') as f:
                            json.dump(output_data, f, ensure_ascii=False, indent=2)
                        
                        print(f"✓ Fixed data saved to aratur_fixed.json")
                        
                        # Show summary of fixes
                        original_invalid = sum(1 for o in offers if o.destination == 'В Партньорство С Абакс')
                        fixed_invalid = sum(1 for o in fixed_offers if o.destination == 'В Партньорство С Абакс')
                        print(f"Offers with invalid destination: {original_invalid} -> {fixed_invalid}")
                        
                    except FileNotFoundError:
                        print("Error: aratur.json not found")
                    except Exception as e:
                        print(f"Error fixing data: {e}")
                    
                    return
                elif arg.isdigit():
                    limit = int(arg)
                    print(f"Limiting to {limit} destinations for testing")
                elif arg.startswith('http'):
                    debug_urls.append(arg)
                else:
                    print(f"Unknown argument: {arg}")
                    print("Usage: python aratour_scraper.py [fix|limit] [url1] [url2] ...")
                    print("Examples:")
                    print("  python aratour_scraper.py fix                 # Fix destinations in existing data")
                    print("  python aratour_scraper.py 1                    # Limit to 1 destination")
                    print("  python aratour_scraper.py https://...          # Test single offer")
                    print("  python aratour_scraper.py https://... https://...  # Test multiple offers")
                    return

            if debug_urls:
                print(f"Debug URLs: {len(debug_urls)}")
                for url in debug_urls:
                    print(f"  - {url}")

        except ValueError:
            print("Usage: python aratour_scraper.py [limit] [url1] [url2] ...")
            return

    async with AratourScraper() as scraper:
        if debug_urls:
            # Debug multiple URLs mode
            print(f"\n=== DEBUG MODE: Testing {len(debug_urls)} URLs ===")
            scraper._debug_mode = True  # Enable debug mode

            all_debug_offers = []

            for i, debug_url in enumerate(debug_urls, 1):
                print(f"\n[{i}/{len(debug_urls)}] Processing: {debug_url}")

                # Check if it's an individual offer URL or main page
                if '/почивка/' in debug_url or '/екскурзия/' in debug_url or '/tour/' in debug_url:
                    # Individual offer URL - create a mock offer and extract details
                    print("Detected individual offer URL, extracting details directly...")
                    offer = AratourOffer(
                        title="Debug Offer",
                        link=debug_url,
                        price="",
                        dates=""
                    )

                    # Fetch and process the offer directly
                    async with scraper.session.get(debug_url) as response:
                        html = await response.text()

                    # Save debug HTML
                    debug_dir = Path("dev")
                    debug_dir.mkdir(exist_ok=True)
                    debug_file = debug_dir / f"debug_offer_{debug_url.split('/')[-1]}.html"
                    async with aiofiles.open(debug_file, 'w', encoding='utf-8') as f:
                        await f.write(html)
                    print(f"✓ Saved debug HTML: {debug_file}")

                    # Extract details
                    await scraper._extract_offer_details_with_html(offer, html)

                    # Print results
                    print(f"Title: {offer.title}")
                    print(f"Price: {offer.price}")
                    print(f"Dates: {offer.dates}")
                    print(f"Destination: {offer.destination}")

                    all_debug_offers.append(offer)

                else:
                    # Main page URL - extract offers from main page
                    async with scraper.session.get(debug_url) as response:
                        html = await response.text()

                    # Extract offers from the page
                    offers = scraper.extract_offers_from_main_page(html, debug_url)
                    print(f"Found {len(offers)} offers on the page")

                    # Extract detailed information from individual offer pages
                    print(f"Extracting detailed information from {len(offers)} offers...")
                    for j, offer in enumerate(offers, 1):
                        if j % 5 == 0:
                            print(f"Processed {j}/{len(offers)} offers...")

                        # Extract details for main page offers
                        await scraper.extract_offer_details(offer)

                    all_debug_offers.extend(offers)

            # Export all debug results to JSON
            output_data = [offer.to_dict() for offer in all_debug_offers]
            with open('aratur.json', 'w', encoding='utf-8') as f:
                json.dump(output_data, f, ensure_ascii=False, indent=2)
            print(f"\n✓ Exported {len(all_debug_offers)} debug offers to JSON: aratur.json")

            print(f"Debug complete for {len(debug_urls)} URLs")
        else:
            # Normal scraping mode
            offers = await scraper.scrape_all_destinations(limit=limit)
            if offers:
                await scraper.save_results()

            print("\n=== SCRAPE COMPLETE ===")
            print(f"Total offers: {len(offers)}")


if __name__ == "__main__":
    import sys
    asyncio.run(main())