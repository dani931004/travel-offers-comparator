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
    """Data structure for Aratour offers with detailed information."""
    title: str = ""
    link: str = ""
    price: str = ""
    description: str = ""
    destination: str = ""
    dates: str = ""  # Travel dates
    duration: str = ""  # Duration in days
    scraped_at: str = field(default_factory=lambda: datetime.now().isoformat())

    # Detailed fields extracted from individual offer pages
    program_info: str = ""
    price_includes: List[str] = field(default_factory=list)
    price_excludes: List[str] = field(default_factory=list)
    hotel_titles: List[str] = field(default_factory=list)
    booking_conditions: str = ""

    # Hotel options with prices
    hotel_options: List[Dict[str, str]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert offer to dictionary for JSON serialization."""
        return {
            'title': self.title,
            'link': self.link,
            'price': self.price,
            'dates': self.dates,
            'description': self.description,
            'destination': self.destination,
            'duration': self.duration,
            'program_info': self.program_info,
            'price_includes': self.price_includes,
            'price_excludes': self.price_excludes,
            'hotel_titles': self.hotel_titles,
            'booking_conditions': self.booking_conditions,
            'hotel_options': self.hotel_options,
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

                    # Extract destination name from URL or link text
                    path = urlparse(full_url).path
                    name = path.split('/')[-1].replace('-', ' ').title()

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
        destination_name = path.split('/')[-1].replace('-', ' ').title()

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

            # Extract destination from URL or context
            path = urlparse(offer.link).path
            destination = path.split('/')[-2] if len(path.split('/')) > 2 else path.split('/')[-1]
            offer.destination = destination.replace('-', ' ').title()

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
                "dates": offer.dates
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
        Extract detailed information from HTML content.
        """
        soup = BeautifulSoup(html, 'html.parser')

        # Clean HTML for better parsing
        for script in soup(["script", "style"]):
            script.decompose()

        # Extract program information (day-by-day itinerary)
        program_info = ""

        # Extract hotel information first (before checking programa content)
        hotel_titles = []

        # First try to find program in the tabbed content structure
        programa_div = soup.find('div', class_='programa')
        if programa_div:
            # Extract hotel titles from programa div before checking content
            hotel_links = programa_div.find_all('a', class_='hotel-item')
            for link in hotel_links:
                title_elem = link.find('h2', class_='title')
                if title_elem:
                    hotel_name = title_elem.get_text().strip()
                    if hotel_name and hotel_name not in hotel_titles:
                        hotel_titles.append(hotel_name)

            # Get all text from the programa div
            program_text = programa_div.get_text(separator='\n').strip()
            # Skip if this is hotel selection content (not actual program)
            if not program_text.startswith('Изберете хотели за резервация по програмата') and len(program_text) > 100:
                program_info = program_text[:3000]

        # If still no program info, look for program section with heading
        if not program_info:
            program_section = soup.find('div', string=re.compile(r'Програма по дни', re.IGNORECASE))
            if program_section:
                # Find the next div or section that contains the program
                program_container = program_section.find_next(['div', 'section'])
                if program_container:
                    program_text = program_container.get_text().strip()
                    if len(program_text) > 100:
                        program_info = program_text[:3000]

        # If still no program info, look for any content with "Ден 1", "Ден 2", etc.
        if not program_info:
            program_patterns = [
                r'Ден\s+\d+.*?(?=В цената|$)',
                r'Програма.*?(?=В цената|$)',
            ]
            for pattern in program_patterns:
                match = re.search(pattern, html, re.DOTALL | re.IGNORECASE)
                if match:
                    program_info = match.group(0).strip()[:3000]
                    break

        # Final fallback: use meta description if it contains program information
        if not program_info:
            meta_desc = soup.find('meta', attrs={'name': 'description'})
            if meta_desc and meta_desc.get('content'):
                meta_content = meta_desc['content']
                # Check if meta description mentions program or excursions
                if any(word in meta_content.lower() for word in ['програма', 'екскурзии', 'екскурзия']):
                    program_info = f"Програма според описанието: {meta_content}"[:3000]

        offer.program_info = program_info

        # Extract price includes
        price_includes = []

        # Look for tabbed content structure first
        tabs_container = soup.find('div', class_='resp-tabs-container')
        if tabs_container:
            tabs = tabs_container.find_all('div', recursive=False)
            tab_names = ['Програма', 'Цената включва', 'Цената не включва', 'Други']
            
            # Find the "Цената включва" tab
            for i, tab in enumerate(tabs):
                if i < len(tab_names) and 'Цената включва' in tab_names[i]:
                    # Extract items from this tab
                    tab_text = tab.get_text(separator='\n').strip()
                    
                    # Split by semicolons and clean up
                    items = [item.strip() for item in tab_text.split(';') if item.strip()]
                    
                    # Filter out non-price-include items (like program descriptions)
                    for item in items:
                        # Skip if it looks like program description or other content
                        if len(item) > 5 and not any(skip in item.lower() for skip in [
                            'програма', 'ден 1', 'ден 2', 'ден 3', 'ден 4', 'ден 5', 'ден 6',
                            'екскурзия', 'пояснения', 'условия', 'договор'
                        ]):
                            # Check if it looks like a price include item
                            if any(keyword in item.lower() for keyword in [
                                'билет', 'такси', 'трансфер', 'хотел', 'закуска', 'водач',
                                'автобус', 'екскурзовод', 'застраховка', 'багаж', 'нощувк'
                            ]):
                                price_includes.append(item)
                    
                    if price_includes:
                        break

        # Fallback to old method if tabbed structure didn't work
        if not price_includes:
            # Look for "ЦЕНАТА ВКЛЮЧВА:" heading and get the following ul/li elements
            includes_heading = soup.find(['p', 'strong', 'div'], string=re.compile(r'ЦЕНАТА ВКЛЮЧВА', re.IGNORECASE))
            if includes_heading:
                # Find the next ul element
                includes_ul = includes_heading.find_next('ul')
                if includes_ul:
                    li_elements = includes_ul.find_all('li')
                    for li in li_elements:
                        text = li.get_text().strip()
                        if text and len(text) > 5:
                            price_includes.append(text)

            # If not found, look for "В цената са включени:" (used in some offers)
            if not price_includes:
                includes_heading = soup.find(['span', 'strong', 'div'], string=re.compile(r'В цената са включени', re.IGNORECASE))
                if includes_heading:
                    # Find the next ul element
                    includes_ul = includes_heading.find_next('ul')
                    if includes_ul:
                        li_elements = includes_ul.find_all('li')
                        for li in li_elements:
                            text = li.get_text().strip()
                            if text and len(text) > 5:
                                price_includes.append(text)

            # If still not found, try the old method as fallback
            if not price_includes:
                includes_section = soup.find(['div', 'p', 'section'], string=re.compile(r'В цената са включени|Цената включва', re.IGNORECASE))
                if includes_section:
                    # Find the next element that contains the list
                    includes_container = includes_section.find_next(['ul', 'div', 'p'])
                    if includes_container:
                        includes_text = includes_container.get_text()
                        # Split by bullet points or line breaks
                        includes_items = re.split(r'[•♦▪■]\s*|\n\s*\n', includes_text)
                        price_includes = [item.strip() for item in includes_items if item.strip() and len(item.strip()) > 5][:20]

            # If still not found, look for ul elements in the programa tab that come after program content
            if not price_includes:
                programa_div = soup.find('div', class_='programa')
                if programa_div:
                    # Find ul elements that come after the programa div
                    next_divs = programa_div.find_all_next('div')
                    for div in next_divs:
                        ul_elements = div.find_all('ul')
                        for ul in ul_elements:
                            li_elements = ul.find_all('li')
                            if li_elements:
                                # Check if this looks like price includes (contains typical items)
                                li_texts = [li.get_text().strip() for li in li_elements]
                                if any('билет' in text.lower() or 'трансфер' in text.lower() or 'застраховка' in text.lower() or 'хотел' in text.lower() for text in li_texts):
                                    # This looks like price includes
                                    price_includes = li_texts[:20]
                                    break
                        if price_includes:
                            break

        offer.price_includes = price_includes[:20]

        # Extract price excludes
        price_excludes = []

        # Look for tabbed content structure first
        tabs_container = soup.find('div', class_='resp-tabs-container')
        if tabs_container:
            tabs = tabs_container.find_all('div', recursive=False)
            tab_names = ['Програма', 'Цената включва', 'Цената не включва', 'Други']
            
            # Find the "Цената не включва" tab
            for i, tab in enumerate(tabs):
                if i < len(tab_names) and 'Цената не включва' in tab_names[i]:
                    # Extract items from this tab
                    tab_text = tab.get_text(separator='\n').strip()
                    
                    # Split by semicolons and clean up
                    items = [item.strip() for item in tab_text.split(';') if item.strip()]
                    
                    # Filter out non-price-exclude items
                    for item in items:
                        # Skip if it looks like program description or other content
                        if len(item) > 5 and not any(skip in item.lower() for skip in [
                            'програма', 'ден 1', 'ден 2', 'ден 3', 'ден 4', 'ден 5', 'ден 6',
                            'екскурзия', 'пояснения', 'условия', 'договор'
                        ]):
                            # Check if it looks like a price exclude item
                            if any(keyword in item.lower() for keyword in [
                                'такси', 'билети', 'слушалки', 'застраховка', 'такса',
                                'горивна', 'инфлационна', 'разходи', 'личен'
                            ]):
                                price_excludes.append(item)
                    
                    if price_excludes:
                        break

        # Fallback to old method if tabbed structure didn't work
        if not price_excludes:
            # Look for "ЦЕНАТА НЕ ВКЛЮЧВА:" heading and get the following ul/li elements
            excludes_heading = soup.find(['p', 'strong', 'div'], string=re.compile(r'ЦЕНАТА НЕ ВКЛЮЧВА|Цената не включва', re.IGNORECASE))
            if excludes_heading:
                # Find the next ul element
                excludes_ul = excludes_heading.find_next('ul')
                if excludes_ul:
                    li_elements = excludes_ul.find_all('li')
                    for li in li_elements:
                        text = li.get_text().strip()
                        if text and len(text) > 5:
                            price_excludes.append(text)

                # Also look for "Задължителни доплащания" section that follows
                mandatory_heading = soup.find(['p', 'strong'], string=re.compile(r'Задължителни доплащания', re.IGNORECASE))
                if mandatory_heading:
                    mandatory_ul = mandatory_heading.find_next('ul')
                    if mandatory_ul:
                        li_elements = mandatory_ul.find_all('li')
                        for li in li_elements:
                            text = li.get_text().strip()
                            if text and len(text) > 5:
                                price_excludes.append(text)

            # If not found, look for "В цената не са включени:" (used in some offers)
            if not price_excludes:
                excludes_heading = soup.find(['span', 'strong', 'div'], string=re.compile(r'В цената не са включени', re.IGNORECASE))
                if excludes_heading:
                    # Find the next ul element
                    excludes_ul = excludes_heading.find_next('ul')
                    if excludes_ul:
                        li_elements = excludes_ul.find_all('li')
                        for li in li_elements:
                            text = li.get_text().strip()
                            if text and len(text) > 5:
                                price_excludes.append(text)

            # If still not found, try the old method as fallback
            if not price_excludes:
                excludes_section = soup.find(['div', 'p', 'section'], string=re.compile(r'В цената не са включени|Цената не включва', re.IGNORECASE))
                if excludes_section:
                    excludes_container = excludes_section.find_next(['ul', 'div', 'p'])
                    if excludes_container:
                        excludes_text = excludes_container.get_text()
                        # Split by bullet points or line breaks
                        excludes_items = re.split(r'[•♦▪■]\s*|\n\s*\n', excludes_text)
                        price_excludes = [item.strip() for item in excludes_items if item.strip() and len(item.strip()) > 5][:20]

            # If still not found, look for ul elements in the programa tab that look like price excludes
            if not price_excludes:
                programa_div = soup.find('div', class_='programa')
                if programa_div:
                    # Find ul elements that come after the programa div
                    next_divs = programa_div.find_all_next('div')
                    for div in next_divs:
                        ul_elements = div.find_all('ul')
                        for ul in ul_elements:
                            li_elements = ul.find_all('li')
                            if li_elements:
                                # Check if this looks like price excludes (contains typical items)
                                li_texts = [li.get_text().strip() for li in li_elements]
                                if any('лични разходи' in text.lower() or 'доплащане' in text.lower() or 'spa' in text.lower() for text in li_texts):
                                    # This looks like price excludes
                                    price_excludes = li_texts[:20]
                                    break
                        if price_excludes:
                            break

        offer.price_excludes = price_excludes[:20]

        # Extract hotel information (already started above)
        # Continue with additional hotel extraction methods if needed

        # If no hotels found in programa div, look for hotel mentions in the content
        if not hotel_titles:
            hotel_patterns = [
                r'хотел\s+([A-Z][a-zA-Z\s]+\d+\*)',
                r'([A-Z][a-zA-Z\s]+(?:\d+\*|\s+хотел))',
            ]
            for pattern in hotel_patterns:
                matches = re.findall(pattern, html, re.IGNORECASE)
                for match in matches:
                    hotel_name = match.strip()
                    if hotel_name and len(hotel_name) > 3 and hotel_name not in hotel_titles:
                        hotel_titles.append(hotel_name[:100])

        offer.hotel_titles = hotel_titles[:10]

        # Extract booking conditions
        booking_conditions = []

        # Look for tabbed content structure first - conditions are in "Други" tab
        tabs_container = soup.find('div', class_='resp-tabs-container')
        if tabs_container:
            tabs = tabs_container.find_all('div', recursive=False)
            tab_names = ['Програма', 'Цената включва', 'Цената не включва', 'Други']
            
            # Find the "Други" tab
            for i, tab in enumerate(tabs):
                if i < len(tab_names) and 'Други' in tab_names[i]:
                    # Extract conditions from this tab
                    ul_elements = tab.find_all('ul')
                    for ul in ul_elements:
                        li_elements = ul.find_all('li')
                        for li in li_elements:
                            text = li.get_text().strip()
                            if text and len(text) > 10:  # Conditions tend to be longer
                                booking_conditions.append(text)
                    
                    if booking_conditions:
                        break

        # Fallback to old method if tabbed structure didn't work
        if not booking_conditions:
            # Look for payment/booking conditions in the tabbed content
            payment_heading = soup.find(['p', 'strong', 'div'], string=re.compile(r'ПЛАЩАНЕ И СРОКОВЕ|Условия за резервация', re.IGNORECASE))
            if payment_heading:
                # Find the next ul element or get text from the section
                payment_ul = payment_heading.find_next('ul')
                if payment_ul:
                    li_elements = payment_ul.find_all('li')
                    for li in li_elements:
                        text = li.get_text().strip()
                        if text and len(text) > 5:
                            booking_conditions.append(text)

                # Also get any following text
                payment_container = payment_heading.find_next('p')
                if payment_container and payment_container.get_text().strip():
                    booking_conditions.append(payment_container.get_text().strip())

            # Fallback to old method
            if not booking_conditions:
                conditions_patterns = [
                    r'Условия за резервация.*?(?=Необходими документи|$)',
                    r'Необходими документи.*?(?=Срокове|$)',
                    r'Срокове за анулации.*?(?=$|ХОТЕЛИ)',
                    r'ПЛАЩАНЕ И СРОКОВЕ.*?(?=$|ХОТЕЛИ)',
                ]

                for pattern in conditions_patterns:
                    match = re.search(pattern, html, re.DOTALL | re.IGNORECASE)
                    if match:
                        condition_text = match.group(0).strip()
                        if len(condition_text) > 20:
                            booking_conditions.append(condition_text)

        if booking_conditions:
            offer.booking_conditions = ' '.join(booking_conditions)[:1000]

        # Extract dates if available - prioritize main offer dates
        main_dates = []

        # Look for date in offer-info sections (most accurate)
        offer_info_elements = soup.find_all('div', class_='offer-info')
        for offer_info in offer_info_elements:
            # Look specifically for the calendar icon offer-info
            if offer_info.find('span', class_='icon-calendar') or 'icon-calendar' in str(offer_info):
                date_text = offer_info.get_text().strip()
                # Extract all dates from this calendar offer-info section
                dates_found = re.findall(r'(\d{1,2}[./-]\d{1,2}[./-]\d{4})', date_text)
                if dates_found:
                    main_dates = dates_found
                    break  # Found the calendar dates, stop looking

        # If no dates found in offer-info, look for dates in reservation links
        if not main_dates:
            reservation_links = soup.find_all('a', href=re.compile(r'reservation\.php|запитване', re.IGNORECASE))
            for link in reservation_links:
                # Check if the link has a date parameter
                href = link.get('href', '')
                date_match = re.search(r'date=(\d{1,2}[./-]\d{1,2}[./-]\d{4})', href)
                if date_match:
                    main_dates.append(date_match.group(1))

                # Also check link text
                link_text = link.get_text().strip()
                dates_found = re.findall(r'\d{1,2}[./-]\d{1,2}[./-]\d{4}', link_text)
                main_dates.extend(dates_found)

        # If we found main dates, use those; otherwise look for any dates on the page
        if not main_dates:
            # Fallback: Look for date patterns in the entire HTML (but avoid hotel option dates)
            date_matches = re.findall(r'(\d{1,2}[./-]\d{1,2}[./-]\d{4})', html)
            # Filter out dates that are likely from hotel options (usually many dates in a row)
            # Only take the first few dates to avoid collecting hotel option dates
            main_dates = date_matches[:10]  # Limit to first 10 dates

        # Remove duplicates and sort dates chronologically
        unique_dates = list(set(main_dates))
        
        # Sort dates chronologically, not alphabetically
        def parse_date(date_str):
            """Parse date string in DD.MM.YYYY or DD/MM/YYYY or DD-MM-YYYY format."""
            try:
                # Normalize separators
                normalized = date_str.replace('/', '.').replace('-', '.')
                day, month, year = normalized.split('.')
                return datetime(int(year), int(month), int(day))
            except (ValueError, IndexError):
                # If parsing fails, return a default date for sorting
                return datetime(1900, 1, 1)
        
        # Sort by actual date value
        unique_dates.sort(key=parse_date)
        
        # Format the dates field - show main date or range
        if unique_dates:
            if len(unique_dates) == 1:
                offer.dates = unique_dates[0]
            elif len(unique_dates) <= 3:
                # Show all dates if few
                offer.dates = ", ".join(unique_dates)
            else:
                # Show range from earliest to latest with count
                offer.dates = f"{unique_dates[0]} - {unique_dates[-1]} (and {len(unique_dates)-2} more dates)"
        
        # Extract price from the offer page (more accurate than main page)
        price_elements = soup.find_all('div', class_='price')
        for price_elem in price_elements:
            price_text = price_elem.get_text().strip()
            # Look for pattern like "от 772.83 лв. / 395.14 €"
            full_price_match = re.search(r'от\s+(\d+(?:[,.]\d+)?)\s*лв\.?\s*/\s*(\d+(?:[,.]\d+)?)\s*€', price_text, re.IGNORECASE)
            if full_price_match:
                offer.price = f"{full_price_match.group(1)} лв. / {full_price_match.group(2)} €"
                break
            # Fallback to simpler pattern
            simple_price_match = re.search(r'(\d+(?:[,.]\d+)?)\s*(лв\.?|€|\$|USD)', price_text)
            if simple_price_match and not offer.price:
                offer.price = simple_price_match.group(0)
                break
                offer.price = f"{full_price_match.group(1)} лв. / {full_price_match.group(2)} €"
                break
            # Fallback to simpler pattern
            simple_price_match = re.search(r'(\d+(?:,\d+)?)\s*(лв\.?|€|\$|USD)', price_text)
            if simple_price_match and not offer.price:
                offer.price = simple_price_match.group(0)
                break

        # Extract hotel options with prices (if available)
        hotel_options = []
        # Look for hotel selection sections
        hotel_selectors = soup.find_all('a', href=re.compile(r'hotel-pochivka'))
        for selector in hotel_selectors:
            hotel_info = {
                'name': selector.get_text().strip(),
                'link': urljoin(self.BASE_URL, selector.get('href')),
                'price': ''
            }

            # Try to find price in the same container
            container = selector.parent
            if container:
                price_match = re.search(r'(\d+(?:,\d+)?)\s*(лв\.?|€|\$|USD)', container.get_text())
                if price_match:
                    hotel_info['price'] = price_match.group(0)

            if hotel_info['name']:
                hotel_options.append(hotel_info)

        offer.hotel_options = hotel_options[:20]


async def main():
    """Main scraping function."""
    limit = None
    debug_url = None

    if len(sys.argv) > 1:
        try:
            if sys.argv[1].startswith('http'):
                debug_url = sys.argv[1]
                limit = int(sys.argv[2]) if len(sys.argv) > 2 else None
            else:
                limit = int(sys.argv[1])
                debug_url = sys.argv[2] if len(sys.argv) > 2 and sys.argv[2].startswith('http') else None
            if limit:
                print(f"Limiting to {limit} destinations for testing")
            if debug_url:
                print(f"Debug URL: {debug_url}")
        except ValueError:
            print("Usage: python aratour_scraper.py [limit] [debug_url]")
            print("Or: python aratour_scraper.py debug_url [limit]")
            return

    async with AratourScraper() as scraper:
        if debug_url:
            # Debug single URL mode
            print(f"\n=== DEBUG MODE: Testing single URL ===")
            scraper._debug_mode = True  # Enable debug mode
            
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
                print(f"\n=== DEBUG RESULTS ===")
                print(f"Title: {offer.title}")
                print(f"Price: {offer.price}")
                print(f"Dates: {offer.dates}")
                
                # Export to JSON
                output_data = [offer.to_dict()]
                with open('aratur.json', 'w', encoding='utf-8') as f:
                    json.dump(output_data, f, ensure_ascii=False, indent=2)
                print(f"✓ Exported to JSON: aratur.json")
                
            else:
                # Main page URL - extract offers from main page
                async with scraper.session.get(debug_url) as response:
                    html = await response.text()
                
                # Extract offers from the page
                offers = scraper.extract_offers_from_main_page(html, debug_url)
                print(f"Found {len(offers)} offers on the page")
                
                # Extract detailed information from individual offer pages
                print(f"\nExtracting detailed information from {len(offers)} offers...")
                for i, offer in enumerate(offers, 1):
                    if i % 5 == 0:
                        print(f"Processed {i}/{len(offers)} offers...")
                    
                    # Extract details for main page offers
                    await scraper.extract_offer_details(offer)
                
                # Save results
                scraper.scraped_offers = offers
                await scraper.save_results()
            print(f"Debug complete for: {debug_url}")
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