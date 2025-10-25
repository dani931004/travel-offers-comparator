#!/usr/bin/env python3
"""
Bohemia.bg scraper using Playwright for JavaScript-rendered content.
Scrapes travel offers from https://bohemia.bg/
Strategy: First discover all destinations, then scrape offers for each destination
"""

import re
import asyncio
import aiohttp
from dataclasses import dataclass, asdict
from datetime import datetime
from typing import List, Dict, Any, Optional
from bs4 import BeautifulSoup
from playwright_scraper_base import PlaywrightScraperBase, BaseOffer, run_scraper


@dataclass
class BohemiaOffer(BaseOffer):
    """Data structure for Bohemia.bg travel offers"""
    pass


class BohemiaScraper(PlaywrightScraperBase):
    """Scraper for Bohemia.bg using Playwright"""
    
    def __init__(self, base_url: str, output_file: str, debug: bool = False, no_enrich: bool = False, batch_size: int = 50, pw_concurrency: int = 5, dot_mmdd: bool = False):
        super().__init__(base_url, output_file, debug)
        self.destinations_discovered = []
        self.no_enrich = no_enrich
        self.batch_size = batch_size
        self.pw_concurrency = max(1, pw_concurrency)
        self.dot_mmdd = dot_mmdd
        self._pw_semaphore = asyncio.Semaphore(self.pw_concurrency)

    def _normalize_date(self, s: str) -> Optional[str]:
        """Normalize a date string to DD.MM.YYYY handling MM/DD/YYYY, DD.MM.YYYY, MM.DD.YYYY."""
        try:
            s = s.strip()
            if '/' in s:
                # Assume MM/DD/YYYY unless dot_mmdd flag flips it to DD/MM/YYYY
                parts = s.split('/')
                if len(parts) == 3:
                    a, b, y = parts
                    ia, ib = int(a), int(b)
                    if self.dot_mmdd:
                        # Treat as DD/MM/YYYY
                        dd, mm = a, b
                    else:
                        # Treat as MM/DD/YYYY
                        mm, dd = a, b
                    return f"{int(dd):02d}.{int(mm):02d}.{y}"
            if '.' in s:
                a, b, y = s.split('.')
                ia, ib = int(a), int(b)
                # If second part > 12, it's MM.DD.YYYY -> swap
                if ib > 12 and ia <= 12:
                    mm, dd, yyyy = a, b, y
                    return f"{int(dd):02d}.{int(mm):02d}.{yyyy}"
                # Else assume DD.MM.YYYY
                dd, mm, yyyy = a, b, y
                return f"{int(dd):02d}.{int(mm):02d}.{yyyy}"
        except Exception:
            return None
        return None
        
    def parse_price(self, price_text: str) -> str:
        """Extract numeric price from text"""
        if not price_text:
            return ""
        
        # Remove whitespace and extract numbers
        price_text = price_text.strip()
        
        # Try to find price with currency (EUR, BGN, лв, etc.)
        patterns = [
            r'(\d+\.?\d*)\s*(EUR|€)',
            r'(\d+\.?\d*)\s*(BGN|лв\.?)',
            r'(\d+\.?\d*)\s*лв',
            r'(\d+\.?\d*)',  # Just numbers as fallback
        ]
        
        for pattern in patterns:
            match = re.search(pattern, price_text, re.IGNORECASE)
            if match:
                price = match.group(1)
                currency = match.group(2) if len(match.groups()) > 1 else 'лв.'
                return f"{price} {currency}"
        
        return price_text
    
    def parse_dates(self, date_text: str) -> str:
        """Extract date range from text"""
        if not date_text:
            return ""
        
        date_text = date_text.strip()
        
        # Look for date patterns like "15.11.2024 - 22.11.2024" or "15.11 - 22.11.2024"
        date_range_pattern = r'(\d{1,2}\.\d{1,2}\.?\d{0,4})\s*-\s*(\d{1,2}\.\d{1,2}\.?\d{0,4})'
        match = re.search(date_range_pattern, date_text)
        
        if match:
            start_date = match.group(1)
            end_date = match.group(2)
            
            # Ensure both dates have year
            if '.' in end_date and len(end_date.split('.')) == 3:
                year = end_date.split('.')[-1]
                if '.' in start_date and len(start_date.split('.')) == 2:
                    start_date = f"{start_date}.{year}"
            
            return f"{start_date} - {end_date}"
        
        # Look for single date
        single_date_pattern = r'\d{1,2}\.\d{1,2}\.?\d{0,4}'
        match = re.search(single_date_pattern, date_text)
        if match:
            return match.group(0)
        
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
        }
        
        for key, value in destinations.items():
            if key in combined_text:
                return value
        
        return "Unknown"
    
    async def discover_destinations(self) -> List[Dict[str, str]]:
        """
        Discover all available destinations from the main navigation.
        Returns list of {name, url} dictionaries.
        """
        if self.debug:
            print("Discovering destinations...")
        
        # Navigate to destinations page
        destinations_url = "https://www.bohemia.bg/Направления/"
        html_content = await self.fetch_page(destinations_url, timeout=30000)
        
        soup = BeautifulSoup(html_content, 'html.parser')
        destinations = []
        
        # Look for destination links - try multiple selectors
        selectors = [
            'a[href*="/Направления/"]',
            'a[href*="направления"]',
            'div.destination a',
            'a[class*="destination"]',
        ]
        
        for selector in selectors:
            links = soup.select(selector)
            if links and self.debug:
                print(f"Found {len(links)} destination links with selector: {selector}")
            
            for link in links:
                href = link.get('href', '')
                text = link.get_text(strip=True)
                
                # Skip if empty or just navigation
                if not text or len(text) < 3:
                    continue
                    
                # Make absolute URL
                if href and not href.startswith('http'):
                    href = f"https://www.bohemia.bg{href}"
                
                if href and text and href not in [d['url'] for d in destinations]:
                    destinations.append({
                        'name': text,
                        'url': href
                    })
        
        if self.debug:
            print(f"Discovered {len(destinations)} unique destinations")
            for dest in destinations[:10]:  # Show first 10
                print(f"  - {dest['name']}: {dest['url']}")
        
        self.destinations_discovered = destinations
        return destinations
    
    def _extract_all_dates_from_html(self, html_content: str) -> List[str]:
        """Extract dates from HTML and return as DD.MM.YYYY sorted unique list.
        Heuristic: infer month/day for dot-separated values using months seen in slash-based dates.
        """
        dates_found = set()
        known_months = set()
        # 1) JSON-like key pairs: "Date":"MM/DD/YYYY" (case-insensitive)
        for m in re.findall(r'"(?:[Dd]ate|[Ss]tart[Dd]ate|[Dd]eparture[Dd]ate)"\s*:\s*"(\d{1,2}/\d{1,2}/\d{4})"', html_content):
            norm = self._normalize_date(m)
            if norm:
                dates_found.add(norm)
                try:
                    known_months.add(int(norm.split('.')[1]))
                except Exception:
                    pass
        # 2) Standalone MM/DD/YYYY
        for m in re.findall(r'\b(\d{1,2}/\d{1,2}/\d{4})\b', html_content):
            norm = self._normalize_date(m)
            if norm:
                dates_found.add(norm)
                try:
                    known_months.add(int(norm.split('.')[1]))
                except Exception:
                    pass
        # 3) Dot-separated occurrences (MM.DD.YYYY or DD.MM.YYYY) with heuristic
        dot_tokens = re.findall(r'\b(\d{1,2}\.\d{1,2}\.\d{4})\b', html_content)
        months_as_second = set()
        for raw in dot_tokens:
            try:
                _, b2, _ = raw.split('.')
                months_as_second.add(int(b2))
            except Exception:
                pass
        for raw in dot_tokens:
            try:
                a, b, y = raw.split('.')
                ia, ib = int(a), int(b)
                if self.dot_mmdd:
                    # Force MM.DD -> DD.MM
                    dd, mm = b, a
                else:
                    # If either side > 12, it's unambiguous dd.mm
                    if ib > 12 and ia <= 31:
                        dd, mm = a, b
                        try:
                            known_months.add(int(mm))
                        except Exception:
                            pass
                    elif ia > 12 and ib <= 12:
                        # a cannot be month; treat as dd.mm
                        dd, mm = a, b
                        try:
                            known_months.add(int(mm))
                        except Exception:
                            pass
                    else:
                        # Ambiguous (both <=12). If first part matches a known month from slash dates, interpret as mm.dd
                        if (ia in known_months or ia in months_as_second) and ib <= 12:
                            dd, mm = b, a  # mm.dd -> dd.mm
                        else:
                            dd, mm = a, b  # default to dd.mm
                norm = f"{int(dd):02d}.{int(mm):02d}.{int(y):04d}"
                dates_found.add(norm)
            except Exception:
                continue
        # Return sorted by real date
        dates_list = sorted(dates_found, key=lambda d: datetime.strptime(d, '%d.%m.%Y'))
        return dates_list

    async def extract_date_range_from_offer_playwright(self, offer_url: str) -> tuple:
        """
        Extract first and last available dates from an individual offer page.
        
        Args:
            offer_url: URL of the offer detail page
            
        Returns:
            Tuple of (first_date, last_date) in DD.MM.YYYY format, or (None, None)
        """
        try:
            # Create a new page for this request to allow parallel processing
            page = await self.context.new_page()
            # Faster wait; then attempt to expose RATESDATA
            await page.goto(offer_url, wait_until='domcontentloaded', timeout=12000)
            # Try clicking typical tabs that reveal dates/prices, best-effort
            tab_texts = [
                'Свободни дати', 'Дати и цени', 'дати и цени', 'Дати', 'дати', 'Цени', 'цени',
                'Дати на отпътуване', 'дати на отпътуване'
            ]
            for txt in tab_texts:
                try:
                    await page.click(f"text={txt}", timeout=1500)
                    await asyncio.sleep(0.4)
                    break
                except Exception:
                    continue
            # Wait for window.RATESDATA if it becomes available
            try:
                await page.wait_for_function("() => window.RATESDATA && window.RATESDATA.length > 0", timeout=6000)
            except Exception:
                pass
            rates_data = await page.evaluate("() => window.RATESDATA || []")
            html_content = await page.content()
            await page.close()
            dates: List[str] = []
            if rates_data:
                for rate in rates_data:
                    if isinstance(rate, dict) and 'Date' in rate:
                        date_str = rate['Date']
                        norm = self._normalize_date(str(date_str))
                        if norm:
                            dates.append(norm)
            # If no dates from window, try parsing HTML directly
            if not dates:
                dates = self._extract_all_dates_from_html(html_content)
            # As a last resort, scan visible text in the document via JS for dates
            if not dates:
                try:
                    # Re-open briefly to evaluate on the DOM
                    page2 = await self.context.new_page()
                    await page2.goto(offer_url, wait_until='domcontentloaded', timeout=8000)
                    visible_dates = await page2.evaluate(
                        "() => {\n"
                        "  const txt = document.body.innerText || '';\n"
                        "  const r1 = /(\\d{1,2}\\.\\d{1,2}\\.\\d{4})/g;\n"
                        "  const r2 = /(\\d{1,2}\\/\\d{1,2}\\/\\d{4})/g;\n"
                        "  const set = new Set();\n"
                        "  let m;\n"
                        "  while ((m = r1.exec(txt)) !== null) set.add(m[1]);\n"
                        "  while ((m = r2.exec(txt)) !== null) {\n"
                        "    const [mm, dd, yyyy] = m[1].split('/');\n"
                        "    const dd2 = ('0'+dd).slice(-2);\n"
                        "    const mm2 = ('0'+mm).slice(-2);\n"
                        "    set.add(`${dd2}.${mm2}.${yyyy}`);\n"
                        "  }\n"
                        "  return Array.from(set);\n"
                        "}"
                    )
                    await page2.close()
                    if visible_dates and isinstance(visible_dates, list):
                        normed = []
                        for d in visible_dates:
                            if isinstance(d, str):
                                nd = self._normalize_date(d)
                                if nd:
                                    normed.append(nd)
                        dates = normed
                except Exception:
                    pass
            if dates:
                # Final normalization pass to be safe
                final_dates: List[str] = []
                for d in dates:
                    if isinstance(d, str):
                        nd = self._normalize_date(d)
                        if nd:
                            final_dates.append(nd)
                if final_dates:
                    final_dates.sort(key=lambda d: datetime.strptime(d, '%d.%m.%Y'))
                    return final_dates[0], final_dates[-1]
            return None, None
        except Exception as e:
            # Close page if it was created but not closed due to exception
            try:
                await page.close()
            except Exception:
                pass
            if self.debug:
                print(f"    Error (PW) fetching dates from {offer_url}: {e}")
            return None, None

    async def extract_date_range_from_offer_http(self, session: aiohttp.ClientSession, offer_url: str, timeout: int = 8) -> tuple:
        """Fast path: fetch offer page via HTTP and parse dates without a browser."""
        try:
            async with session.get(offer_url, timeout=timeout) as resp:
                if resp.status != 200:
                    return None, None
                html_content = await resp.text(errors='ignore')
            # Try to parse JSON-ish RATESDATA first
            match = re.search(r'(?:var|let|const)\s+RATESDATA\s*=\s*(\[.*?\]);', html_content, re.DOTALL)
            dates: List[str] = []
            if match:
                import json
                blob = match.group(1)
                try:
                    rates_data = json.loads(blob)
                except Exception:
                    cleaned = re.sub(r"(\w+)\s*:", r'"\1":', blob)
                    cleaned = cleaned.replace("'", '"')
                    rates_data = json.loads(cleaned)
                for rate in rates_data:
                    if isinstance(rate, dict) and 'Date' in rate:
                        norm = self._normalize_date(str(rate['Date']))
                        if norm:
                            dates.append(norm)
            # Fallback 2: inspect external scripts likely containing RATESDATA
            if not dates:
                # Derive product id from URL if present
                pid_match = re.search(r"/(\d{6,})/", offer_url)
                prod_id = pid_match.group(1) if pid_match else None
                script_srcs = re.findall(r'<script[^>]+src=["\']([^"\']+)["\']', html_content, re.IGNORECASE)
                # Build candidate list
                candidates = []
                for src in script_srcs:
                    low = src.lower()
                    if (prod_id and prod_id in low) or any(k in low for k in ['rate', 'dates', 'calendar', 'price']):
                        # Make absolute
                        if src.startswith('http'):
                            candidates.append(src)
                        else:
                            base = 'https://www.bohemia.bg'
                            if not src.startswith('/'):
                                src = '/' + src
                            candidates.append(base + src)
                # Limit to a few to keep fast
                for js_url in candidates[:5]:
                    try:
                        async with session.get(js_url, timeout=min(timeout, 5)) as sresp:
                            if sresp.status != 200:
                                continue
                            js_text = await sresp.text(errors='ignore')
                        # Try RATESDATA JSON pattern in JS
                        m2 = re.search(r'(?:var|let|const)\s+RATESDATA\s*=\s*(\[.*?\]);', js_text, re.DOTALL)
                        if m2:
                            import json
                            blob2 = m2.group(1)
                            try:
                                rates_data2 = json.loads(blob2)
                            except Exception:
                                cleaned2 = re.sub(r"(\w+)\s*:", r'"\1":', blob2)
                                cleaned2 = cleaned2.replace("'", '"')
                                rates_data2 = json.loads(cleaned2)
                            tmp_dates = []
                            for rate in rates_data2:
                                if isinstance(rate, dict) and 'Date' in rate:
                                    norm = self._normalize_date(str(rate['Date']))
                                    if norm:
                                        tmp_dates.append(norm)
                            if tmp_dates:
                                dates = sorted(set(tmp_dates), key=lambda d: datetime.strptime(d, '%d.%m.%Y'))
                                break
                        # Else generic scan in JS
                        if not dates:
                            tmp = self._extract_all_dates_from_html(js_text)
                            if tmp:
                                dates = tmp
                                break
                    except Exception:
                        continue
            if dates:
                dates.sort(key=lambda d: datetime.strptime(d, '%d.%m.%Y'))
                return dates[0], dates[-1]
            return None, None
        except Exception:
            return None, None
    
    async def enrich_offers_with_dates(self, offers: List[BohemiaOffer], batch_size: Optional[int] = None) -> List[BohemiaOffer]:
        """
        Enrich offers with actual date ranges by fetching them in parallel batches.
        
        Args:
            offers: List of offers to enrich
            batch_size: Number of pages to fetch concurrently
            
        Returns:
            List of offers with updated dates
        """
        import time
        total = len(offers)
        if batch_size is None:
            batch_size = self.batch_size
        start_time = time.time()
        
        print(f"🔄 Enriching {total} offers with dates (batch size: {batch_size})...")
        
        # Process offers in batches
        successful_enrichments = 0
        for i in range(0, total, batch_size):
            batch = offers[i:i+batch_size]
            batch_num = (i // batch_size) + 1
            total_batches = (total + batch_size - 1) // batch_size
            
            batch_start = time.time()
            print(f"📦 Processing batch {batch_num}/{total_batches} ({len(batch)} offers)...")
            
            # HTTP fast path for all offers in batch
            headers = {
                'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
                'Accept-Language': 'bg-BG,bg;q=0.9,en-US;q=0.8,en;q=0.7',
                'Connection': 'keep-alive',
            }
            timeout_cfg = aiohttp.ClientTimeout(total=12)
            async with aiohttp.ClientSession(headers=headers, timeout=timeout_cfg) as session:
                http_tasks = [self.extract_date_range_from_offer_http(session, offer.link) for offer in batch]
                http_results = await asyncio.gather(*http_tasks, return_exceptions=True)

            # Update offers with HTTP results; collect fallbacks
            batch_success_http = 0
            need_fallback_idxs = []
            for idx, (offer, result) in enumerate(zip(batch, http_results)):
                if isinstance(result, tuple) and result[0] and result[1]:
                    first_date, last_date = result
                    offer.dates = f"{first_date} - {last_date}"
                    batch_success_http += 1
                    successful_enrichments += 1
                else:
                    need_fallback_idxs.append(idx)

            # Fallback to Playwright for those that failed HTTP path
            batch_success_pw = 0
            if need_fallback_idxs:
                if self.debug:
                    print(f"      Fallback to browser for {len(need_fallback_idxs)} offers...")
                async def _guarded_pw(url: str):
                    async with self._pw_semaphore:
                        return await self.extract_date_range_from_offer_playwright(url)
                pw_tasks = [_guarded_pw(batch[idx].link) for idx in need_fallback_idxs]
                pw_results = await asyncio.gather(*pw_tasks, return_exceptions=True)
                for idx, result in zip(need_fallback_idxs, pw_results):
                    if isinstance(result, tuple) and result[0] and result[1]:
                        first_date, last_date = result
                        batch[idx].dates = f"{first_date} - {last_date}"
                        batch_success_pw += 1
                        successful_enrichments += 1
                    elif isinstance(result, Exception):
                        if self.debug:
                            print(f"      ❌ PW error for {batch[idx].link}: {result}")

            batch_time = time.time() - batch_start
            completed = min(i + batch_size, total)
            print(f"✅ Batch {batch_num} complete: {batch_success_http}+{batch_success_pw}={batch_success_http+batch_success_pw}/{len(batch)} offers got dates ({batch_time:.1f}s). Total progress: {completed}/{total} offers, {successful_enrichments} enriched")

            # Small delay between batches to avoid overwhelming the server
            await asyncio.sleep(0.15)
        
        total_time = time.time() - start_time
        print(f"🎉 Date enrichment complete! {successful_enrichments}/{total} offers enriched in {total_time:.1f}s ({total_time/total:.2f}s per offer)")
        
        return offers
    
    async def scrape_destination(self, destination: Dict[str, str], limit: Optional[int] = None) -> List[BohemiaOffer]:
        """
        Scrape offers for a specific destination.
        
        Args:
            destination: Dictionary with 'name' and 'url'
            limit: Optional max number of offers to return for this destination
            
        Returns:
            List of BohemiaOffer objects
        """
        if self.debug:
            print(f"\nScraping destination: {destination['name']}")
        
        try:
            html_content = await self.fetch_page(
                destination['url'],
                wait_for_selector='body',
                timeout=30000
            )
            
            # Try scrolling to load more
            await self.scroll_to_bottom(scroll_pause_time=1.0, max_scrolls=3)
            html_content = await self.page.content()
            
            offers = await self.extract_offers_from_page(html_content, destination['name'])

            # Apply per-destination limit early to avoid enriching unnecessary offers
            if limit is not None:
                offers = offers[:max(0, limit)]
            
            # Enrich offers with actual date ranges (parallel fetch)
            if offers and not self.no_enrich:
                print(f"📅 Starting date enrichment for {len(offers)} offers from {destination['name']}...")
                offers = await self.enrich_offers_with_dates(offers)
                print(f"📅 Date enrichment complete for {destination['name']}: {len(offers)} offers processed")
            
            if self.debug:
                print(f"  Found {len(offers)} offers for {destination['name']}")
            
            return offers
            
        except Exception as e:
            if self.debug:
                print(f"  Error scraping {destination['name']}: {e}")
            return []
    
    async def extract_offers_from_page(self, html_content: str, destination_name: str = "Unknown") -> List[BohemiaOffer]:
        """Extract offers from HTML content - Bohemia uses a.offer-browser-item structure"""
        soup = BeautifulSoup(html_content, 'html.parser')
        offers = []
        
        # Bohemia uses specific structure: <a class="offer-browser-item">
        offer_elements = soup.select('a.offer-browser-item')
        
        if self.debug:
            print(f"  Found {len(offer_elements)} offer elements for {destination_name}")
        
        if not offer_elements and self.debug:
            print(f"  No offer elements found for {destination_name}")
        
        for element in offer_elements:
            try:
                # Extract link (the <a> element itself)
                link = element.get('href', '')
                if link and not link.startswith('http'):
                    link = f"https://www.bohemia.bg{link}"
                
                # Extract title from div.title > h3
                title = ""
                title_div = element.find('div', class_='title')
                if title_div:
                    h3 = title_div.find('h3')
                    h4 = title_div.find('h4')
                    if h3:
                        title = h3.get_text(strip=True)
                        if h4:
                            subtitle = h4.get_text(strip=True)
                            # Don't include subtitle if too long
                            if len(subtitle) < 50:
                                title = f"{title} - {subtitle}"
                
                # Extract price from div.price > div.amount (EUR price)
                price = ""
                price_div = element.find('div', class_='price')
                if price_div:
                    # Get all amount divs - last one is usually EUR
                    amount_divs = price_div.find_all('div', class_='amount')
                    if amount_divs:
                        # Look for EUR price (contains €)
                        for amt in amount_divs:
                            amt_text = amt.get_text(strip=True)
                            if '€' in amt_text:
                                price = amt_text
                                break
                        # Fallback to last amount if no EUR found
                        if not price:
                            price = amount_divs[-1].get_text(strip=True)
                
                # Extract duration from div.right (e.g., "4 дни")
                duration = ""
                right_div = element.find('div', class_='right')
                if right_div:
                    # Get text, skip transport icon
                    for text_node in right_div.stripped_strings:
                        if 'дни' in text_node or 'ден' in text_node or 'нощувки' in text_node:
                            duration = text_node
                            break
                
                # Do not fetch dates here; batch enrichment will handle it later
                dates = duration or ""
                
                # Use discovered destination name
                destination = destination_name if destination_name != "Unknown" else "Unknown"
                
                # Only add if we have at least title and link
                if title and link and len(title) > 3:
                    offer = BohemiaOffer(
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
                    print(f"  Error parsing offer: {e}")
                continue
        
        return offers
    
    async def scrape(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Main scraping logic.
        First discovers all destinations, then scrapes offers for each.
        """
        all_offers = []
        
        # Step 1: Discover all destinations
        destinations = await self.discover_destinations()
        
        if not destinations:
            if self.debug:
                print("No destinations found! Falling back to hot offers page...")
            # Fallback to hot offers page
            destinations = [{'name': 'Горещи Оферти', 'url': 'https://www.bohemia.bg/Горещи-Оферти/'}]
        
        # Step 2: Scrape offers for each destination
        for i, destination in enumerate(destinations):
            if limit and len(all_offers) >= limit:
                break
                
            print(f"🌍 Scraping destination {i+1}/{len(destinations)}: {destination['name']}")
            remaining = None if limit is None else max(0, limit - len(all_offers))
            if remaining == 0:
                break
            dest_offers = await self.scrape_destination(destination, limit=remaining)
            all_offers.extend(dest_offers)
            
            print(f"✅ Destination {destination['name']} complete: {len(dest_offers)} offers found, total offers: {len(all_offers)}")
            
            if self.debug:
                print(f"Progress: {i+1}/{len(destinations)} destinations, {len(all_offers)} total offers")
            
            # Small delay between destinations to be nice to the server
            if i < len(destinations) - 1:
                await asyncio.sleep(0.5)
        
        # Apply limit if specified
        if limit and len(all_offers) > limit:
            all_offers = all_offers[:limit]
        
        # Convert to dictionaries
        return [asdict(offer) for offer in all_offers]


if __name__ == "__main__":
    import asyncio
    BASE_URL = "https://www.bohemia.bg/"
    OUTPUT_FILE = "bohemia.json"
    
    asyncio.run(run_scraper(
        BohemiaScraper,
        BASE_URL,
        OUTPUT_FILE,
        "Bohemia.bg travel offers scraper"
    ))
