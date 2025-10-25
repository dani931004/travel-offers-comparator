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
from urllib.parse import urlparse, urlunparse, quote


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
        self.discovered_listing_pages: List[str] = []
        
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
            # Catch connection errors, redirects loops, DNS issues, etc.
            print(f"Error fetching {url}: {e}")
            return None

    def _normalize_url(self, href: str) -> Optional[str]:
        """Normalize relative vs absolute URLs and ensure they are internal to BASE_URL."""
        if not href:
            return None
        href = href.strip()
        # Skip useless links
        if any(href.lower().startswith(x) for x in ['mailto:', 'tel:', 'javascript:', '#']):
            return None
        if href.startswith('http'):
            # Only allow same host (root or www), ignore other subdomains
            allowed_hosts = [
                'https://aventura.bg',
                'http://aventura.bg',
                'https://www.aventura.bg',
                'http://www.aventura.bg',
            ]
            if not any(href.startswith(h) for h in allowed_hosts):
                return None
            # Prefer https and canonicalize www -> root
            href = href.replace('http://', 'https://')
            if href.startswith('https://www.aventura.bg'):
                href = 'https://aventura.bg' + href[len('https://www.aventura.bg'):]
            # Sanitize path (encode spaces, ampersands in path, etc.)
            try:
                parts = urlparse(href)
                safe_path = quote(parts.path, safe="/:%()-._~")
                href = urlunparse((parts.scheme, parts.netloc, safe_path, parts.params, parts.query, parts.fragment))
            except Exception:
                pass
            return href
        # Make absolute
        if href.startswith('/'):
            return f"{self.BASE_URL}{href}"
        return f"{self.BASE_URL}/{href}"

    def _is_offer_detail_url(self, href: str) -> bool:
        """Heuristic: detail pages start with /pochivka/ or /ekskurzia/"""
        try:
            path = href.split('aventura.bg')[-1]
            return path.startswith('/pochivka/') or path.startswith('/ekskurzia/')
        except Exception:
            return False

    def _count_offer_links(self, html: str) -> int:
        soup = BeautifulSoup(html, 'html.parser')
        links = soup.find_all('a', href=True)
        cnt = 0
        for a in links:
            href = a.get('href', '')
            norm = self._normalize_url(href)
            if not norm:
                continue
            if self._is_offer_detail_url(norm.replace('https://', 'https://')):
                cnt += 1
        return cnt

    async def discover_listing_pages(self, max_pages: int = 100) -> List[str]:
        """Discover listing/destination pages by crawling internal links up to shallow depth.
        Strategy: start from homepage, collect internal links; any page with >=5 offer detail links is a listing page.
        Avoid adding detail pages themselves. Limit total to max_pages.
        """
        print("Discovering listing pages...")
        start_url = self.OFFERS_URL
        visited = set()
        queue = [start_url]
        listings: List[str] = []

        while queue and len(listings) < max_pages:
            url = queue.pop(0)
            if url in visited:
                continue
            visited.add(url)

            html = await self.fetch_page(url)
            if not html:
                continue

            # Count offers on this page
            offer_count = self._count_offer_links(html)
            if offer_count >= 5 and not self._is_offer_detail_url(url):
                listings.append(url)
                print(f"Listing page: {url} (offers: {offer_count})")

            # Enqueue more internal links (limited breadth)
            soup = BeautifulSoup(html, 'html.parser')
            for a in soup.find_all('a', href=True):
                norm = self._normalize_url(a.get('href', ''))
                if not norm:
                    continue
                # Only consider likely listing/category pages to avoid deep crawling of detail slugs
                try:
                    p = urlparse(norm)
                    path = p.path or '/'
                except Exception:
                    path = '/'
                allowed_listing_prefixes = (
                    '/',
                    '/ранни-записвания',
                    '/препоръчани',
                    '/kalendar.php',
                    '/pochivki.php',
                    '/pochivki',
                    '/pochivki-garcia',
                )
                # Skip obvious detail pages and non-listing-like paths
                if self._is_offer_detail_url(norm):
                    continue
                if not any(path == prefix or path.startswith(prefix + '/') or path.startswith(prefix + '?') for prefix in allowed_listing_prefixes):
                    continue
                if norm not in visited and norm not in queue and len(visited) + len(queue) < 300:
                    queue.append(norm)

        # Always include homepage if not already
        if start_url not in listings:
            listings.insert(0, start_url)

        # De-duplicate while preserving order
        seen = set()
        ordered = []
        for u in listings:
            if u not in seen:
                seen.add(u)
                ordered.append(u)

        self.discovered_listing_pages = ordered[:max_pages]
        print(f"Discovered {len(self.discovered_listing_pages)} listing pages")
        return self.discovered_listing_pages
            
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

    def parse_price_from_html(self, html: str) -> str:
        """Extract price from entire HTML text, prefer EUR, fallback to BGN."""
        soup = BeautifulSoup(html, 'html.parser')
        text = soup.get_text(separator=' ', strip=True)

        # Prefer explicit EUROS in DOM spans first
        span_texts = ' '.join([span.get_text(strip=True) for span in soup.find_all('span')])
        m_eur = re.search(r'(\d+[\d\s,\.]*)\s*€', span_texts)
        if m_eur:
            num = m_eur.group(1).replace(' ', '').replace(',', '.')
            return f"{num} EUR"

        # Fallback to any EUR in full text
        m_eur2 = re.search(r'(\d+[\d\s,\.]*)\s*€', text)
        if m_eur2:
            num = m_eur2.group(1).replace(' ', '').replace(',', '.')
            return f"{num} EUR"

        # Try BGN patterns (лв or BGN)
        m_bgn = re.search(r'(\d+[\d\s,\.]*)\s*(лв\.?|BGN)', text, re.IGNORECASE)
        if m_bgn:
            num = m_bgn.group(1).replace(' ', '').replace(',', '.')
            return f"{num} BGN"

        return ""
        
    def parse_dates(self, date_text: str) -> str:
        """
        Extract and format dates.
        
        Args:
            date_text: Text containing date info
            
        Returns:
            Formatted date range string
        """
        # Look for dates in DD.MM.YYYY strictly to avoid matching prices
        dates = re.findall(r'\b(\d{1,2}\.\d{1,2}\.\d{4})\b', date_text)

        # Normalize to DD.MM.YYYY with leading zeros
        norm = []
        for d in dates:
            try:
                parts = d.split('.')
                day = int(parts[0])
                month = int(parts[1])
                year = int(parts[2])
                if 1 <= day <= 31 and 1 <= month <= 12 and 2000 <= year <= 2100:
                    norm.append(f"{day:02d}.{month:02d}.{year}")
            except Exception:
                continue

        if not norm:
            return ""

        # Sort as date objects and build range
        from datetime import datetime as _dt
        parsed = sorted({_dt.strptime(x, "%d.%m.%Y") for x in norm})
        start = parsed[0].strftime("%d.%m.%Y")
        end = parsed[-1].strftime("%d.%m.%Y")
        return f"{start} - {end}"

    def parse_dates_from_html(self, html: str) -> str:
        """Extract date range from the whole HTML page."""
        soup = BeautifulSoup(html, 'html.parser')
        text = soup.get_text(separator=' ', strip=True)
        return self.parse_dates(text)
        
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
        # Add common variations/extra countries
        destinations += ['тунис', 'гръцки']
        
        for dest in destinations:
            if dest in text:
                if dest == 'гръцки':
                    return 'Гърция'
                return dest.capitalize()
                
        return "Unknown"

    def extract_destination_from_html(self, html: str, fallback_text: str = "") -> str:
        """Try to extract a cleaner destination from the detail page."""
        soup = BeautifulSoup(html, 'html.parser')
        # Try known location class
        loc = soup.find(['div', 'span'], class_=re.compile(r'(tr-loc|location|loc|дестинац|место)', re.I))
        if loc:
            return loc.get_text(strip=True)
        # Try breadcrumbs
        crumbs = soup.select('ul.breadcrumb li, .breadcrumb a, .breadcrumbs a')
        if crumbs:
            txt = ' - '.join([c.get_text(strip=True) for c in crumbs if c.get_text(strip=True)])
            if txt:
                return txt
        # Fallback to heuristics using only the fallback text (avoid whole-page keywords noise)
        fb = fallback_text or ''
        return self.extract_destination(fb, fb)
        
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
        
        # Limit to desired number of offers
        tasks = []
        sem = asyncio.Semaphore(8)

        async def process_link(idx: int, link_elem):
            if self.limit and len(self.offers) >= self.limit:
                return None
            link = link_elem.get('href', '')
            if not link:
                return None

            # Deduplicate
            if link in self.seen_urls:
                return None
            self.seen_urls.add(link)

            if not link.startswith('http'):
                full_link = self.BASE_URL + link if link.startswith('/') else f"{self.BASE_URL}/{link}"
            else:
                full_link = link
            # Sanitize full link path
            try:
                parts = urlparse(full_link)
                safe_path = quote(parts.path, safe="/:%()-._~")
                full_link = urlunparse((parts.scheme, parts.netloc, safe_path, parts.params, parts.query, parts.fragment))
            except Exception:
                pass

            # Title from listing
            text_content = link_elem.get_text(separator=' ', strip=True)
            title_elem = link_elem.find(['div'], class_=re.compile(r'tleft-title|tright-title|tr-hotel'))
            title = title_elem.get_text(separator=' ', strip=True) if title_elem else text_content
            title = re.sub(r'\s*от\s*\d+[\d\s,\.]*€|\s*от\s*\d+[\d\s,\.]*лв.*', '', title).strip()
            if len(title) < 5:
                return None

            # Destination from listing if available
            loc_elem = link_elem.find(['div'], class_=re.compile(r'tr-loc'))
            dest_hint = loc_elem.get_text(strip=True) if loc_elem else self.extract_destination(title, text_content)

            # Try to parse price from the listing block first (prefer EUR)
            list_price = ''
            m_eur_list = re.search(r'(\d+[\d\s,\.]*)\s*€', text_content)
            if m_eur_list:
                list_price = f"{m_eur_list.group(1).replace(' ', '').replace(',', '.')} EUR"
            else:
                m_bgn_list = re.search(r'(\d+[\d\s,\.]*)\s*(лв\.?|BGN)', text_content, re.IGNORECASE)
                if m_bgn_list:
                    list_price = f"{m_bgn_list.group(1).replace(' ', '').replace(',', '.')} BGN"

            # Enrich from detail page
            async with sem:
                html_detail = await self.fetch_page(full_link)
            if not html_detail:
                price = list_price
                dates = ''
                destination = dest_hint or 'Unknown'
            else:
                # Prefer price from detail page; we'll fallback to listing price later
                detail_price = self.parse_price_from_html(html_detail)
                dates = self.parse_dates_from_html(html_detail)
                destination = self.extract_destination_from_html(html_detail, fallback_text=dest_hint or title)
                # Prefer listing price if available (advertised starting price), else detail price
                price = list_price or detail_price

            # If still no price, try to parse from combined text
            if not price:
                # Try to parse price from the link element's own text
                m_eur = re.search(r'(\d+[\d\s,\.]*)\s*€', text_content)
                m_bgn = re.search(r'(\d+[\d\s,\.]*)\s*(лв\.?|BGN)', text_content, re.IGNORECASE)
                if m_eur:
                    num = m_eur.group(1).replace(' ', '').replace(',', '.')
                    price = f"{num} EUR"
                elif m_bgn:
                    num = m_bgn.group(1).replace(' ', '').replace(',', '.')
                    price = f"{num} BGN"

            # Normalize any non-breaking spaces in price and drop obviously invalid tiny EUR amounts (<20)
            price = price.replace('\xa0', ' ').strip()
            try:
                m_val = re.match(r'^(\d+(?:\.\d+)?)\s*(EUR|BGN)$', price)
                if m_val and m_val.group(2) == 'EUR' and float(m_val.group(1)) < 20:
                    price = ''
            except Exception:
                pass

            # Skip offers without price or date range to avoid incomplete data
            if not price or not dates:
                return None

            offer = AventuraOffer(
                title=title,
                link=full_link,
                price=price,
                dates=dates,
                destination=destination,
                scraped_at=datetime.now().isoformat()
            )

            if self.debug and idx < 3:
                await self.save_debug_html(str(link_elem), f"debug_aventura_offer_{page_num}_{idx}.html")

            return offer

        for idx, link_elem in enumerate(offer_links):
            if self.limit and len(tasks) >= self.limit:
                break
            tasks.append(asyncio.create_task(process_link(idx, link_elem)))

        results = await asyncio.gather(*tasks)
        offers = [o for o in results if o]
        return offers
        
    async def scrape_offers(self):
        """Main scraping logic"""
        print(f"Starting Aventura.bg scraper...")
        print(f"Debug mode: {self.debug}, Limit: {self.limit or 'No limit'}")

        # Discover listing pages
        listings = await self.discover_listing_pages(max_pages=100)
        count_pages = 0
        for idx, url in enumerate(listings, start=1):
            html = await self.fetch_page(url)
            if not html:
                continue
            if self.debug and idx == 1:
                await self.save_debug_html(html, "aventura_offers_page.html")
            page_offers = await self.extract_offers_from_page(html, idx)
            self.offers.extend([o for o in page_offers if o])
            count_pages += 1
            # Respect limit if provided
            if self.limit and len(self.offers) >= self.limit:
                break

        print(f"Processed {count_pages} listing pages; scraped {len(self.offers)} total offers")
        
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
