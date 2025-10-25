"""
Base class for Playwright-based web scrapers.
This module provides a reusable foundation for scraping JavaScript-rendered websites.
"""

import asyncio
import json
from dataclasses import dataclass, asdict
from datetime import datetime
from typing import List, Optional, Dict, Any
from abc import ABC, abstractmethod
from playwright.async_api import async_playwright, Page, Browser, BrowserContext
import argparse


@dataclass
class BaseOffer:
    """Base dataclass for travel offers"""
    title: str
    link: str
    price: str
    dates: str
    destination: str
    scraped_at: str


class PlaywrightScraperBase(ABC):
    """
    Abstract base class for Playwright-based scrapers.
    Handles browser lifecycle, page navigation, and common scraping patterns.
    """
    
    def __init__(self, base_url: str, output_file: str, debug: bool = False):
        self.base_url = base_url
        self.output_file = output_file
        self.debug = debug
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        
    async def __aenter__(self):
        """Async context manager entry - initializes Playwright browser"""
        self.playwright = await async_playwright().start()
        
        # Launch browser in headless mode (always headless now)
        self.browser = await self.playwright.chromium.launch(
            headless=True,  # Always headless
            args=['--disable-blink-features=AutomationControlled']
        )
        
        # Create context with realistic browser settings
        self.context = await self.browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36'
        )
        
        self.page = await self.context.new_page()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit - cleans up browser resources"""
        if self.page:
            await self.page.close()
        if self.context:
            await self.context.close()
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()
    
    async def fetch_page(self, url: str, wait_for_selector: Optional[str] = None, timeout: int = 30000) -> str:
        """
        Fetch a page and optionally wait for specific selector to appear.
        
        Args:
            url: URL to fetch
            wait_for_selector: CSS selector to wait for before returning content
            timeout: Maximum time to wait in milliseconds
            
        Returns:
            HTML content of the page
        """
        if self.debug:
            print(f"Fetching: {url}")
            
        await self.page.goto(url, wait_until='networkidle', timeout=timeout)
        
        # Wait for specific selector if provided
        if wait_for_selector:
            try:
                await self.page.wait_for_selector(wait_for_selector, timeout=timeout)
                if self.debug:
                    print(f"Found selector: {wait_for_selector}")
            except Exception as e:
                if self.debug:
                    print(f"Warning: Selector '{wait_for_selector}' not found: {e}")
        
        # Add a small delay to ensure dynamic content is loaded
        await asyncio.sleep(1)
        
        content = await self.page.content()
        return content
    
    async def scroll_to_bottom(self, scroll_pause_time: float = 0.5, max_scrolls: int = 10):
        """
        Scroll to the bottom of the page to trigger lazy loading.
        
        Args:
            scroll_pause_time: Time to wait between scrolls (seconds)
            max_scrolls: Maximum number of scroll operations
        """
        for i in range(max_scrolls):
            # Get current scroll height
            prev_height = await self.page.evaluate('document.body.scrollHeight')
            
            # Scroll down
            await self.page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
            
            # Wait for new content to load
            await asyncio.sleep(scroll_pause_time)
            
            # Check if we've reached the bottom
            new_height = await self.page.evaluate('document.body.scrollHeight')
            if new_height == prev_height:
                break
                
        if self.debug:
            print(f"Completed {i + 1} scrolls")
    
    async def click_load_more(self, button_selector: str, max_clicks: int = 5, wait_time: float = 1.0):
        """
        Click "Load More" button multiple times to load additional content.
        
        Args:
            button_selector: CSS selector for the load more button
            max_clicks: Maximum number of times to click
            wait_time: Time to wait after each click (seconds)
        """
        for i in range(max_clicks):
            try:
                # Check if button exists and is visible
                button = await self.page.query_selector(button_selector)
                if not button:
                    if self.debug:
                        print(f"Load more button not found after {i} clicks")
                    break
                    
                # Click the button
                await button.click()
                await asyncio.sleep(wait_time)
                
                if self.debug:
                    print(f"Clicked load more button {i + 1} times")
                    
            except Exception as e:
                if self.debug:
                    print(f"Error clicking load more: {e}")
                break
    
    def save_debug_html(self, content: str, filename: str):
        """Save HTML content to debug file"""
        debug_path = f"dev/{filename}"
        with open(debug_path, 'w', encoding='utf-8') as f:
            f.write(content)
        if self.debug:
            print(f"Saved debug HTML to {debug_path}")
    
    def save_results(self, offers: List[Dict[str, Any]]):
        """Save scraped offers to JSON file"""
        with open(self.output_file, 'w', encoding='utf-8') as f:
            json.dump(offers, f, ensure_ascii=False, indent=2)
        print(f"Saved {len(offers)} offers to {self.output_file}")
    
    # Abstract methods that must be implemented by subclasses
    
    @abstractmethod
    async def extract_offers_from_page(self, html_content: str) -> List[BaseOffer]:
        """
        Extract offers from HTML content.
        Must be implemented by subclass.
        
        Args:
            html_content: HTML content of the page
            
        Returns:
            List of offer objects
        """
        pass
    
    @abstractmethod
    async def scrape(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Main scraping logic.
        Must be implemented by subclass.
        
        Args:
            limit: Maximum number of offers to scrape (None for all)
            
        Returns:
            List of offer dictionaries
        """
        pass


def create_argparser(description: str) -> argparse.ArgumentParser:
    """Create a standard argument parser for scrapers"""
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument('--debug', action='store_true', help='Enable debug mode with visible browser')
    parser.add_argument('--limit', type=int, default=20, help='Limit number of offers to scrape (0 for all)')
    # Performance and behavior tuning
    parser.add_argument('--no-enrich', action='store_true', help='Skip date enrichment (faster, shows duration only)')
    parser.add_argument('--batch-size', type=int, default=50, help='Concurrent HTTP detail fetches per batch for date enrichment')
    parser.add_argument('--pw-concurrency', type=int, default=5, help='Max concurrent Playwright pages for fallback enrichment')
    parser.add_argument('--dot-mmdd', action='store_true', help='Treat dot-separated dates as MM.DD.YYYY (flip to DD.MM.YYYY)')
    return parser


async def run_scraper(scraper_class, base_url: str, output_file: str, description: str):
    """
    Standard entry point for running a scraper.
    
    Args:
        scraper_class: The scraper class to instantiate
        base_url: Base URL for the website
        output_file: Output JSON file path
        description: Description for argument parser
    """
    parser = create_argparser(description)
    args = parser.parse_args()
    
    limit = None if args.limit == 0 else args.limit
    
    print(f"Starting {scraper_class.__name__}...")
    print(f"Debug mode: {args.debug}")
    print(f"Limit: {'No limit' if limit is None else limit}")
    
    async with scraper_class(
        base_url,
        output_file,
        debug=args.debug,
        no_enrich=getattr(args, 'no_enrich', False),
        batch_size=getattr(args, 'batch_size', 50),
        pw_concurrency=getattr(args, 'pw_concurrency', 5),
        dot_mmdd=getattr(args, 'dot_mmdd', False),
    ) as scraper:
        offers = await scraper.scrape(limit=limit)
        scraper.save_results(offers)
        
    print(f"Scraped {len(offers)} total offers")
