#!/usr/bin/env python3
"""
Aratour Issues Fixer - Fix all data quality issues by fetching fresh data from URLs

This script addresses all issues found by analyze_aratur_data.py by:
- Fetching actual HTML from each offer URL
- Re-extracting data using the scraper's logic
- Updating offers with accurate, current information
"""

import json
import re
import asyncio
import aiohttp
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Any

async def fetch_and_fix_offer(offer_data: Dict[str, Any], session: aiohttp.ClientSession) -> Dict[str, Any]:
    """Fetch fresh data from offer URL and update the offer."""
    url = offer_data.get('link', '')
    if not url:
        return offer_data

    try:
        print(f"  Fetching: {url}")
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=30)) as response:
            html = await response.text()

        # Create a temporary offer object for extraction
        temp_offer = {
            'title': offer_data.get('title', ''),
            'link': url,
            'price': '',
            'dates': '',
            'destination': ''
        }

        # Extract data from HTML using the same logic as the scraper
        updated_offer = extract_offer_details_from_html(temp_offer, html)

        # Update original offer with fresh data
        offer_data.update({
            'price': updated_offer.get('price', offer_data.get('price', '')),
            'dates': updated_offer.get('dates', offer_data.get('dates', '')),
            'destination': updated_offer.get('destination', offer_data.get('destination', ''))
        })

        print(f"    Updated: dates='{offer_data['dates']}', dest='{offer_data['destination']}', price='{offer_data['price']}'")
        return offer_data

    except Exception as e:
        print(f"    Error fetching {url}: {e}")
        return offer_data


def extract_offer_details_from_html(offer: Dict[str, Any], html: str) -> Dict[str, Any]:
    """Extract offer details from HTML using the same logic as the scraper."""
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html, 'html.parser')

    # Clean HTML
    for script in soup(["script", "style"]):
        script.decompose()

    # Extract price
    price_patterns = [
        r'(\d{3,5}(?:[.,]\d{2})?)\s*лв',
        r'цена от\s*(\d{3,5}(?:[.,]\d{2})?)\s*лв',
    ]
    page_text = soup.get_text(separator='\n')
    for pattern in price_patterns:
        match = re.search(pattern, page_text)
        if match:
            offer['price'] = f"{match.group(1)} лв."
            break

    # Extract dates
    if not offer['dates'] or offer['dates'].strip() == "":
        # First try: Find spans with 'до' and dates
        date_spans = soup.find_all('span', string=lambda text: text and 'до' in text and re.search(r'\d{1,2}[./-]\d{1,2}[./-]\d{4}', text))
        if date_spans:
            date_text = date_spans[0].get_text().strip()
            date_pattern = r'(\d{1,2}[./-]\d{1,2}[./-]\d{4})'
            all_dates = re.findall(date_pattern, date_text)
            if all_dates:
                from datetime import datetime
                parsed_dates = [datetime.strptime(d.replace('-', '.'), "%d.%m.%Y") for d in all_dates]
                parsed_dates.sort()
                first_date = parsed_dates[0].strftime("%d.%m.%Y")
                last_date = parsed_dates[-1].strftime("%d.%m.%Y")
                offer['dates'] = f"{first_date} - {last_date}" if first_date != last_date else first_date
        else:
            # Second try: Calendar spans
            calendar_spans = soup.find_all('span', class_='icon-calendar')
            for calendar_span in calendar_spans:
                parent_div = calendar_span.find_parent('div', class_='offer-info')
                if parent_div:
                    div_text = parent_div.get_text().strip()
                    if re.search(r'\d{1,2}[./-]\d{1,2}[./-]\d{4}', div_text):
                        date_pattern = r'(\d{1,2}[./-]\d{1,2}[./-]\d{4})'
                        all_dates = re.findall(date_pattern, div_text)
                        if all_dates:
                            from datetime import datetime
                            parsed_dates = [datetime.strptime(d.replace('-', '.'), "%d.%m.%Y") for d in all_dates]
                            parsed_dates.sort()
                            first_date = parsed_dates[0].strftime("%d.%m.%Y")
                            last_date = parsed_dates[-1].strftime("%d.%m.%Y")
                            offer['dates'] = f"{first_date} - {last_date}" if first_date != last_date else first_date
                            break

    # If single date and multi-day trip, calculate return date
    if offer['dates'] and '-' not in offer['dates']:
        duration_match = re.search(r'(\d+)\s*дни\s*/\s*(\d+)\s*нощувки', page_text)
        if duration_match:
            days = int(duration_match.group(1))
            if days > 1:
                from datetime import datetime, timedelta
                try:
                    dep_date = datetime.strptime(offer['dates'], "%d.%m.%Y")
                    ret_date = dep_date + timedelta(days=days - 1)
                    offer['dates'] = f"{offer['dates']} - {ret_date.strftime('%d.%m.%Y')}"
                except ValueError:
                    pass

    # Extract destination
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

    title_elem = soup.find('title')
    if title_elem:
        title_text = title_elem.get_text().strip()
        destination_patterns = [
            r'([А-ЯA-Z][а-яА-Яa-zA-Z\s]+)\s+\d{4}\s*–',
            r'Aratour\s*-\s*([А-ЯA-Z][а-яА-Яa-zA-Z\s]+)',
            r'Екскурзия\s+до\s+([А-ЯA-Z][а-яА-Яa-zA-Z\s]+)',
            r'Почивка\s+в\s+([А-ЯA-Z][а-яА-Яa-zA-Z\s]+)',
            r'([А-ЯA-Z][а-яА-Яa-zA-Z\s]+)\s*-\s*Aratour',
            r'([А-ЯA-Z][а-яА-Яa-zA-Z\s]+)\s+ИМПЕРСКИТЕ',
            r'([А-ЯA-Z][а-яА-Яa-zA-Z\s]+)\s+–\s+МИСТИКА',
            r'([А-ЯA-Z][а-яА-Яa-zA-Z\s]+)\s+–\s+ЗЕМЯ',
            r'([А-ЯA-Z][а-яА-Яa-zA-Z\s]+)\s+–\s+\d+',
            r'([А-ЯA-Z][а-яА-Яa-zA-Z\s]+)\s+40\s+НЮАНСА',
        ]
        for pattern in destination_patterns:
            match = re.search(pattern, title_text, re.IGNORECASE)
            if match:
                extracted_dest = match.group(1).strip()
                if extracted_dest in known_destinations:
                    offer['destination'] = extracted_dest
                    break

    return offer


def load_offers(json_path: str) -> List[Dict[str, Any]]:
    """Load offers from JSON file."""
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"Error: {json_path} not found")
        return []


def save_offers(offers: List[Dict[str, Any]], json_path: str) -> None:
    """Save offers to JSON file."""
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(offers, f, ensure_ascii=False, indent=2)
    print(f"✓ Saved {len(offers)} offers to {json_path}")


async def fix_offers_with_fresh_data(offers: List[Dict[str, Any]]) -> int:
    """Fix offers by fetching fresh data from their URLs."""
    fixed_count = 0

    async with aiohttp.ClientSession() as session:
        for i, offer in enumerate(offers):
            print(f"Processing offer [{i}]: {offer.get('title', '')[:50]}...")

            # Check if offer needs fixing (has issues)
            needs_fixing = (
                not offer.get('dates') or offer.get('dates', '').strip() == '' or
                not offer.get('destination') or offer.get('destination', '').strip() == '' or
                not offer.get('price') or offer.get('price', '').strip() == ''
            )

            if needs_fixing:
                original_data = {
                    'dates': offer.get('dates', ''),
                    'destination': offer.get('destination', ''),
                    'price': offer.get('price', '')
                }

                updated_offer = await fetch_and_fix_offer(offer, session)

                # Check if data actually changed
                if (updated_offer.get('dates') != original_data['dates'] or
                    updated_offer.get('destination') != original_data['destination'] or
                    updated_offer.get('price') != original_data['price']):
                    fixed_count += 1
                    print(f"  ✓ Fixed offer [{i}]")
                else:
                    print(f"  - No changes needed for offer [{i}]")
            else:
                print(f"  - Offer [{i}] already complete")

    return fixed_count


def fix_inconsistent_date_ranges(offers: List[Dict[str, Any]]) -> int:
    """Fix offers with inconsistent date ranges."""
    fixed_count = 0

    for i, offer in enumerate(offers):
        dates = offer.get('dates', '').strip()
        title = offer.get('title', '').lower()

        if '-' not in dates:
            continue

        # Extract duration from title
        duration_days = None
        duration_match = re.search(r'(\d+)\s*дни', title)
        if duration_match:
            duration_days = int(duration_match.group(1))
        else:
            night_match = re.search(r'(\d+)\s*нощувки', title)
            if night_match:
                duration_days = int(night_match.group(1)) + 1

        if not duration_days:
            continue

        try:
            date_parts = dates.split(' - ')
            if len(date_parts) == 2:
                start_date = datetime.strptime(date_parts[0].strip(), "%d.%m.%Y")
                end_date = datetime.strptime(date_parts[1].strip(), "%d.%m.%Y")
                actual_days = (end_date - start_date).days + 1

                # If the range is too short for the duration, extend it
                if actual_days < duration_days and duration_days - actual_days <= 2:  # Allow small adjustments
                    new_end_date = start_date + timedelta(days=duration_days - 1)
                    new_dates = f"{date_parts[0].strip()} - {new_end_date.strftime('%d.%m.%Y')}"
                    offer['dates'] = new_dates
                    fixed_count += 1
                    print(f"  Fixed [{i}]: {dates} -> {new_dates} (duration: {duration_days} days)")
        except ValueError:
            pass  # Invalid date format

    return fixed_count


def fix_invalid_destinations(offers: List[Dict[str, Any]]) -> int:
    """Fix offers with invalid destinations by clearing them so they can be re-extracted."""
    fixed_count = 0

    invalid_keywords = [
        'партньорство', 'partnership', 'абакс', 'abaks',
        'pochi', 'ekskurzi', 'tour', 'пътуван', 'пътешеств', 'vacation', 'trip',
        'early', 'booking', 'ранни', 'записван', 'лято', 'зима', 'пролет', 'есен',
        'all', 'inclusive', 'all-inclusive', 'всичко', 'включен', 'от', 'до', 'в',
        'коледа', 'christmas', 'нова-година', 'new-year', 'великден', 'easter',
        'уикенд', 'weekend', 'екзотични', 'exotic', 'круизи', 'cruises',
        'авторски', 'author', 'специални', 'special', 'промо', 'promo',
        'тръгване', 'departure', 'варна', 'sofia', 'софия', 'burgas', 'бургас',
        'пловдив', 'plovdiv', 'от', 'from', 'летище', 'airport'
    ]

    for i, offer in enumerate(offers):
        destination = offer.get('destination', '').strip()

        if destination:
            dest_lower = destination.lower()
            if any(keyword in dest_lower for keyword in invalid_keywords):
                print(f"  Cleared invalid destination [{i}]: '{destination}' -> ''")
                offer['destination'] = ''
                fixed_count += 1

    return fixed_count


def review_suspicious_prices(offers: List[Dict[str, Any]]) -> None:
    """Review offers with suspiciously high prices."""
    print("\n🔍 REVIEWING SUSPICIOUS PRICES:")
    print("-" * 50)

    for i, offer in enumerate(offers):
        price = offer.get('price', '').strip()
        if price:
            try:
                # Extract numeric value
                numeric_price = float(price.replace('лв.', '').replace('лв', '').replace('€', '').replace(',', '.').strip())
                if numeric_price > 10000:  # Suspiciously high threshold
                    print(f"[{i}] HIGH PRICE: {price}")
                    print(f"    Title: {offer.get('title', '')[:80]}")
                    print(f"    Link: {offer.get('link', '')}")
                    print()
            except ValueError:
                pass


async def main():
    """Main fix function."""
    json_path = "aratur.json"
    backup_path = "aratur_backup.json"

    print("🔧 ARATOUR ISSUES FIXER (Fresh Data Version)")
    print("=" * 50)

    # Load offers
    offers = load_offers(json_path)
    if not offers:
        return

    print(f"Loaded {len(offers)} offers from {json_path}")

    # Create backup
    save_offers(offers, backup_path)
    print(f"✓ Created backup: {backup_path}")

    # Fix offers by fetching fresh data
    print("\n1. Fetching fresh data from offer URLs...")
    fixed_count = await fix_offers_with_fresh_data(offers)
    print(f"   ✓ Updated {fixed_count} offers with fresh data")

    # Review suspicious prices
    print("\n2. Reviewing suspicious prices...")
    review_suspicious_prices(offers)

    # Save fixed data
    save_offers(offers, json_path)

    print(f"\n✅ FIX COMPLETE:")
    print(f"   - Offers updated with fresh data: {fixed_count}")
    print(f"   - Check suspicious prices manually")

    print("\n💡 NEXT STEPS:")
    print("   - Review the suspicious prices manually")
    print("   - Re-run analyzer to verify fixes")


if __name__ == "__main__":
    asyncio.run(main())