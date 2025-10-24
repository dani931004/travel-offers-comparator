#!/usr/bin/env python3
"""
Aratour Data Analyzer - Analyze scraped data for issues and provide fixing recommendations

This script analyzes the aratur.json file and identifies offers with missing or incorrect data,
providing a clear roadmap for fixing the scraper.
"""

import json
import re
from pathlib import Path
from typing import List, Dict, Any
from collections import defaultdict


def load_offers(json_path: str) -> List[Dict[str, Any]]:
    """Load offers from JSON file."""
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"Error: {json_path} not found")
        return []
    except Exception as e:
        print(f"Error loading {json_path}: {e}")
        return []


def analyze_offer_dates(offers: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Analyze date-related issues in offers."""
    issues = {
        'empty_dates': [],
        'invalid_date_format': [],
        'valid_dates': []
    }

    date_pattern = re.compile(r'^\d{1,2}[./-]\d{1,2}[./-]\d{4}(?:\s*-\s*\d{1,2}[./-]\d{1,2}[./-]\d{4})?$')

    for i, offer in enumerate(offers):
        dates = offer.get('dates', '').strip()

        if not dates:
            issues['empty_dates'].append(i)
        elif not date_pattern.match(dates):
            issues['invalid_date_format'].append(i)
        else:
            issues['valid_dates'].append(i)

    return issues


def analyze_offer_prices(offers: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Analyze price-related issues in offers."""
    issues = {
        'empty_prices': [],
        'invalid_price_format': [],
        'suspiciously_low': [],
        'suspiciously_high': [],
        'valid_prices': []
    }

    price_pattern = re.compile(r'^\d+(?:[.,]\d{2})?\s*лв\.?$')

    for i, offer in enumerate(offers):
        price = offer.get('price', '').strip()

        if not price:
            issues['empty_prices'].append(i)
        elif not price_pattern.match(price):
            issues['invalid_price_format'].append(i)
        else:
            # Extract numeric value
            try:
                numeric_price = float(price.replace('лв.', '').replace('лв', '').replace(',', '.').strip())
                if numeric_price < 100:
                    issues['suspiciously_low'].append(i)
                elif numeric_price > 10000:
                    issues['suspiciously_high'].append(i)
                else:
                    issues['valid_prices'].append(i)
            except ValueError:
                issues['invalid_price_format'].append(i)

    return issues


def analyze_offer_destinations(offers: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Analyze destination-related issues in offers."""
    issues = {
        'empty_destinations': [],
        'invalid_destinations': [],
        'valid_destinations': []
    }

    known_destinations = {
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
    }

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

        if not destination:
            issues['empty_destinations'].append(i)
        elif destination not in known_destinations:
            # Check if it contains invalid keywords
            dest_lower = destination.lower()
            if any(keyword in dest_lower for keyword in invalid_keywords):
                issues['invalid_destinations'].append(i)
            else:
                # Could be a valid but unrecognized destination
                issues['valid_destinations'].append(i)
        else:
            issues['valid_destinations'].append(i)

    return issues


def analyze_offer_titles(offers: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Analyze title-related issues in offers."""
    issues = {
        'empty_titles': [],
        'too_short': [],
        'suspicious_titles': [],
        'valid_titles': []
    }

    suspicious_keywords = [
        'debug', 'test', 'sample', 'example', 'template',
        'цена по запитване', 'price on request'
    ]

    for i, offer in enumerate(offers):
        title = offer.get('title', '').strip()

        if not title:
            issues['empty_titles'].append(i)
        elif len(title) < 10:
            issues['too_short'].append(i)
        elif any(keyword.lower() in title.lower() for keyword in suspicious_keywords):
            issues['suspicious_titles'].append(i)
        else:
            issues['valid_titles'].append(i)

    return issues


def analyze_date_consistency(offers: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Analyze date consistency based on duration and content."""
    issues = {
        'single_date_multi_day': [],  # Single date but duration suggests multi-day
        'inconsistent_ranges': [],    # Date ranges that don't match duration
        'valid_date_consistency': []
    }

    for i, offer in enumerate(offers):
        dates = offer.get('dates', '').strip()
        title = offer.get('title', '').lower()
        description = offer.get('description', '').lower() if offer.get('description') else ''

        # Extract duration from title or description
        duration_days = None
        duration_match = re.search(r'(\d+)\s*дни', title + ' ' + description)
        if duration_match:
            duration_days = int(duration_match.group(1))
        else:
            # Check for night-based duration
            night_match = re.search(r'(\d+)\s*нощувки', title + ' ' + description)
            if night_match:
                duration_days = int(night_match.group(1)) + 1  # nights + 1 = days

        # Check if single date but should be range
        if dates and '-' not in dates and duration_days and duration_days > 1:
            # Keywords that suggest round trip
            round_trip_keywords = ['екскурзия', 'тур', 'пътешествие', 'приключение', 'круиз', 'нова година', 'великден', 'коледа']
            if any(keyword in title + ' ' + description for keyword in round_trip_keywords):
                issues['single_date_multi_day'].append(i)
                continue

        # Check date range consistency
        if '-' in dates:
            try:
                date_parts = dates.split(' - ')
                if len(date_parts) == 2:
                    from datetime import datetime
                    start_date = datetime.strptime(date_parts[0].strip(), "%d.%m.%Y")
                    end_date = datetime.strptime(date_parts[1].strip(), "%d.%m.%Y")
                    actual_days = (end_date - start_date).days + 1  # inclusive

                    if duration_days and abs(actual_days - duration_days) > 1:  # Allow 1 day tolerance
                        issues['inconsistent_ranges'].append(i)
                        continue
            except ValueError:
                pass  # Invalid date format

        issues['valid_date_consistency'].append(i)

    return issues


def generate_report(offers: List[Dict[str, Any]]) -> None:
    """Generate a comprehensive analysis report."""
    print("=" * 60)
    print("ARATOUR DATA ANALYSIS REPORT")
    print("=" * 60)
    print(f"Total offers analyzed: {len(offers)}")
    print()

    # Analyze each category
    date_issues = analyze_offer_dates(offers)
    price_issues = analyze_offer_prices(offers)
    destination_issues = analyze_offer_destinations(offers)
    title_issues = analyze_offer_titles(offers)
    date_consistency_issues = analyze_date_consistency(offers)

    # Print summary
    print("📊 SUMMARY:")
    print(f"  ✅ Valid dates: {len(date_issues['valid_dates'])}")
    print(f"  ✅ Valid prices: {len(price_issues['valid_prices'])}")
    print(f"  ✅ Valid destinations: {len(destination_issues['valid_destinations'])}")
    print(f"  ✅ Valid titles: {len(title_issues['valid_titles'])}")
    print(f"  ✅ Valid date consistency: {len(date_consistency_issues['valid_date_consistency'])}")
    print()

    # Print issues by priority
    print("🚨 ISSUES BY PRIORITY:")
    print()

    # High priority: Empty dates
    if date_issues['empty_dates']:
        print(f"🔴 CRITICAL: {len(date_issues['empty_dates'])} offers with EMPTY DATES")
        print("   These offers need immediate attention for date extraction.")
        print(f"   Indices: {date_issues['empty_dates'][:10]}{'...' if len(date_issues['empty_dates']) > 10 else ''}")
        print()

    # High priority: Empty prices
    if price_issues['empty_prices']:
        print(f"🔴 CRITICAL: {len(price_issues['empty_prices'])} offers with EMPTY PRICES")
        print("   These offers need price extraction fixes.")
        print(f"   Indices: {price_issues['empty_prices'][:10]}{'...' if len(price_issues['empty_prices']) > 10 else ''}")
        print()

    # Medium priority: Invalid date formats
    if date_issues['invalid_date_format']:
        print(f"🟡 MEDIUM: {len(date_issues['invalid_date_format'])} offers with INVALID DATE FORMAT")
        print("   Date format doesn't match expected pattern.")
        print(f"   Indices: {date_issues['invalid_date_format'][:10]}{'...' if len(date_issues['invalid_date_format']) > 10 else ''}")
        print()

    # Medium priority: Date consistency issues
    if date_consistency_issues['single_date_multi_day']:
        print(f"🟡 MEDIUM: {len(date_consistency_issues['single_date_multi_day'])} offers with SINGLE DATE but MULTI-DAY DURATION")
        print("   These offers have single dates but duration suggests they should have date ranges.")
        print(f"   Indices: {date_consistency_issues['single_date_multi_day'][:10]}{'...' if len(date_consistency_issues['single_date_multi_day']) > 10 else ''}")
        print()

    if date_consistency_issues['inconsistent_ranges']:
        print(f"🟡 MEDIUM: {len(date_consistency_issues['inconsistent_ranges'])} offers with INCONSISTENT DATE RANGES")
        print("   Date range doesn't match the stated duration.")
        print(f"   Indices: {date_consistency_issues['inconsistent_ranges'][:10]}{'...' if len(date_consistency_issues['inconsistent_ranges']) > 10 else ''}")
        print()

    # Medium priority: Empty destinations
    if destination_issues['empty_destinations']:
        print(f"🟡 MEDIUM: {len(destination_issues['empty_destinations'])} offers with EMPTY DESTINATIONS")
        print("   These offers need destination extraction.")
        print(f"   Indices: {destination_issues['empty_destinations'][:10]}{'...' if len(destination_issues['empty_destinations']) > 10 else ''}")
        print()

    # Medium priority: Invalid destinations
    if destination_issues['invalid_destinations']:
        print(f"🟡 MEDIUM: {len(destination_issues['invalid_destinations'])} offers with INVALID DESTINATIONS")
        print("   These offers have destinations that are not actual travel destinations (departure points, partnerships, etc.).")
        print(f"   Indices: {destination_issues['invalid_destinations'][:10]}{'...' if len(destination_issues['invalid_destinations']) > 10 else ''}")
        print()

    # Low priority: Suspicious prices
    suspicious_prices = len(price_issues['suspiciously_low']) + len(price_issues['suspiciously_high'])
    if suspicious_prices > 0:
        print(f"🟢 LOW: {suspicious_prices} offers with SUSPICIOUS PRICES")
        print(f"   Too low: {len(price_issues['suspiciously_low'])}, Too high: {len(price_issues['suspiciously_high'])}")
        print()

    # Show some examples of problematic offers
    print("🔍 EXAMPLES OF PROBLEMATIC OFFERS:")
    print()

    if date_issues['empty_dates']:
        print("Offers with empty dates:")
        for idx in date_issues['empty_dates'][:3]:
            offer = offers[idx]
            print(f"  [{idx}] {offer.get('title', '')[:50]}... -> {offer.get('link', '')}")

    if price_issues['empty_prices']:
        print("\nOffers with empty prices:")
        for idx in price_issues['empty_prices'][:3]:
            offer = offers[idx]
            print(f"  [{idx}] {offer.get('title', '')[:50]}... -> {offer.get('link', '')}")

    print()
    print("💡 RECOMMENDATIONS:")
    print("1. Focus on fixing EMPTY DATES first - these are critical for the travel offers")
    print("2. Then fix EMPTY PRICES - users need pricing information")
    print("3. Finally address EMPTY DESTINATIONS - improves search/filtering")
    print("4. Test fixes on a few examples before applying to all offers")
    print()

    # Save detailed report
    report_path = Path("data_analysis_report.txt")
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write("ARATOUR DATA ANALYSIS REPORT\n")
        f.write("=" * 50 + "\n\n")

        f.write("DETAILED ISSUES:\n\n")

        f.write(f"Empty dates ({len(date_issues['empty_dates'])}):\n")
        for idx in date_issues['empty_dates']:
            offer = offers[idx]
            f.write(f"  [{idx}] {offer.get('title', '')[:60]} | {offer.get('link', '')}\n")
        f.write("\n")

        f.write(f"Empty prices ({len(price_issues['empty_prices'])}):\n")
        for idx in price_issues['empty_prices']:
            offer = offers[idx]
            f.write(f"  [{idx}] {offer.get('title', '')[:60]} | {offer.get('link', '')}\n")
        f.write("\n")

        f.write(f"Empty destinations ({len(destination_issues['empty_destinations'])}):\n")
        for idx in destination_issues['empty_destinations']:
            offer = offers[idx]
            f.write(f"  [{idx}] {offer.get('title', '')[:60]} | {offer.get('link', '')}\n")
        f.write("\n")

        f.write(f"Invalid destinations ({len(destination_issues['invalid_destinations'])}):\n")
        for idx in destination_issues['invalid_destinations']:
            offer = offers[idx]
            f.write(f"  [{idx}] {offer.get('title', '')[:60]} | Destination: {offer.get('destination', '')}\n")

    print(f"📄 Detailed report saved to: {report_path}")


def main():
    """Main analysis function."""
    json_path = "aratur.json"

    print("Loading offers from aratur.json...")
    offers = load_offers(json_path)

    if not offers:
        print("No offers found. Run the scraper first.")
        return

    generate_report(offers)


if __name__ == "__main__":
    main()