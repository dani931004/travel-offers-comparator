#!/usr/bin/env python3
"""
Dari Tour Data Analyzer - Analyze scraped data for issues and provide fixing recommendations

This script analyzes the dari_tour_scraped.json file and identifies offers with missing or incorrect data,
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
        'Австралия', 'Нова Зеландия', 'Сингапур', 'Банкок', 'Тайланд',
        'Бразилия', 'Рио де Жанейро', 'Дубай', 'ОАЕ', 'Индия', 'Португалия',
        'Русия', 'Москва', 'Санкт Петербург', 'Доминикана', 'Куба', 'Мексико',
        'Япония', 'Китай', 'Виетнам', 'Филипини', 'Малайзия', 'Индонезия',
        'Южна Корея', 'Тайван', 'Израел', 'Йордания', 'Ливан', 'Турция',
        'Гърция', 'Италия', 'Испания', 'Франция', 'Германия', 'Австрия',
        'Швейцария', 'Чехия', 'Полша', 'Унгария', 'Румъния', 'България',
        'Сърбия', 'Хърватия', 'Словения', 'Черна гора', 'Албания', 'Македония',
        'Великобритания', 'Ирландия', 'Нидерландия', 'Белгия', 'Швеция',
        'Норвегия', 'Дания', 'Финландия', 'Естония', 'Латвия', 'Литва',
        'САЩ', 'Канада', 'Аржентина', 'Чили', 'Перу', 'Колумбия', 'Еквадор',
        'Боливия', 'Уругвай', 'Парагвай', 'Мароко', 'Тунис', 'Египет',
        'Кения', 'Танзания', 'ЮАР', 'Намибия', 'Замбия', 'Зимбабве', 'Малави',
        'Мозамбик', 'Мадагаскар', 'Сейшелски острови', 'Мавриций', 'Реюнион'
    }

    for i, offer in enumerate(offers):
        destination = offer.get('destination', '').strip()

        if not destination:
            issues['empty_destinations'].append(i)
        elif destination not in known_destinations:
            issues['invalid_destinations'].append(i)
        else:
            issues['valid_destinations'].append(i)

    return issues


def analyze_offer_titles(offers: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Analyze title-related issues in offers."""
    issues = {
        'empty_titles': [],
        'too_short_titles': [],
        'valid_titles': []
    }

    for i, offer in enumerate(offers):
        title = offer.get('title', '').strip()

        if not title:
            issues['empty_titles'].append(i)
        elif len(title) < 10:
            issues['too_short_titles'].append(i)
        else:
            issues['valid_titles'].append(i)

    return issues


def analyze_offer_links(offers: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Analyze link-related issues in offers."""
    issues = {
        'empty_links': [],
        'invalid_links': [],
        'valid_links': []
    }

    url_pattern = re.compile(r'^https?://[^\s/$.?#].[^\s]*$')

    for i, offer in enumerate(offers):
        link = offer.get('link', '').strip()

        if not link:
            issues['empty_links'].append(i)
        elif not url_pattern.match(link):
            issues['invalid_links'].append(i)
        else:
            issues['valid_links'].append(i)

    return issues


def generate_report(offers: List[Dict[str, Any]]) -> str:
    """Generate a comprehensive analysis report."""
    print("Loading offers from dari_tour_scraped.json...")
    total_offers = len(offers)
    print(f"Total offers analyzed: {total_offers}")

    # Analyze each field
    date_analysis = analyze_offer_dates(offers)
    price_analysis = analyze_offer_prices(offers)
    destination_analysis = analyze_offer_destinations(offers)
    title_analysis = analyze_offer_titles(offers)
    link_analysis = analyze_offer_links(offers)

    # Calculate percentages
    def calc_percent(count): return f"{count/total_offers*100:.1f}%" if total_offers > 0 else "0%"

    report = f"""
{'='*50}
DARI TOUR DATA ANALYSIS REPORT
{'='*50}
Total offers analyzed: {total_offers}

📊 SUMMARY:
  ✅ Valid dates: {len(date_analysis['valid_dates'])} ({calc_percent(len(date_analysis['valid_dates']))})
  ✅ Valid prices: {len(price_analysis['valid_prices'])} ({calc_percent(len(price_analysis['valid_prices']))})
  ✅ Valid destinations: {len(destination_analysis['valid_destinations'])} ({calc_percent(len(destination_analysis['valid_destinations']))})
  ✅ Valid titles: {len(title_analysis['valid_titles'])} ({calc_percent(len(title_analysis['valid_titles']))})
  ✅ Valid links: {len(link_analysis['valid_links'])} ({calc_percent(len(link_analysis['valid_links']))})

🚨 ISSUES BY PRIORITY:

"""

    # High priority issues
    if date_analysis['empty_dates']:
        report += f"🔴 HIGH: {len(date_analysis['empty_dates'])} offers with EMPTY DATES\n"
        report += f"   Indices: {date_analysis['empty_dates'][:10]}{'...' if len(date_analysis['empty_dates']) > 10 else ''}\n\n"

    if price_analysis['empty_prices']:
        report += f"🔴 HIGH: {len(price_analysis['empty_prices'])} offers with EMPTY PRICES\n"
        report += f"   Indices: {price_analysis['empty_prices'][:10]}{'...' if len(price_analysis['empty_prices']) > 10 else ''}\n\n"

    if link_analysis['empty_links']:
        report += f"🔴 HIGH: {len(link_analysis['empty_links'])} offers with EMPTY LINKS\n"
        report += f"   Indices: {link_analysis['empty_links'][:10]}{'...' if len(link_analysis['empty_links']) > 10 else ''}\n\n"

    # Medium priority issues
    if date_analysis['invalid_date_format']:
        report += f"🟡 MEDIUM: {len(date_analysis['invalid_date_format'])} offers with INVALID DATE FORMATS\n"
        report += f"   Date format should be DD.MM.YYYY or DD.MM.YYYY - DD.MM.YYYY\n"
        report += f"   Indices: {date_analysis['invalid_date_format'][:10]}{'...' if len(date_analysis['invalid_date_format']) > 10 else ''}\n\n"

    if price_analysis['invalid_price_format']:
        report += f"🟡 MEDIUM: {len(price_analysis['invalid_price_format'])} offers with INVALID PRICE FORMATS\n"
        report += f"   Price format should be: 1234.56 лв.\n"
        report += f"   Indices: {price_analysis['invalid_price_format'][:10]}{'...' if len(price_analysis['invalid_price_format']) > 10 else ''}\n\n"

    if destination_analysis['empty_destinations']:
        report += f"🟡 MEDIUM: {len(destination_analysis['empty_destinations'])} offers with EMPTY DESTINATIONS\n"
        report += f"   Indices: {destination_analysis['empty_destinations'][:10]}{'...' if len(destination_analysis['empty_destinations']) > 10 else ''}\n\n"

    if destination_analysis['invalid_destinations']:
        report += f"🟡 MEDIUM: {len(destination_analysis['invalid_destinations'])} offers with INVALID DESTINATIONS\n"
        report += f"   Destinations not in known list\n"
        report += f"   Indices: {destination_analysis['invalid_destinations'][:10]}{'...' if len(destination_analysis['invalid_destinations']) > 10 else ''}\n\n"

    # Low priority issues
    if price_analysis['suspiciously_low']:
        report += f"🟢 LOW: {len(price_analysis['suspiciously_low'])} offers with SUSPICIOUSLY LOW PRICES\n"
        report += f"   Prices under 100 лв. may be incorrect\n"
        report += f"   Indices: {price_analysis['suspiciously_low'][:10]}{'...' if len(price_analysis['suspiciously_low']) > 10 else ''}\n\n"

    if price_analysis['suspiciously_high']:
        report += f"🟢 LOW: {len(price_analysis['suspiciously_high'])} offers with SUSPICIOUSLY HIGH PRICES\n"
        report += f"   Prices over 10,000 лв. may be special/luxury offers\n"
        report += f"   Indices: {price_analysis['suspiciously_high'][:10]}{'...' if len(price_analysis['suspiciously_high']) > 10 else ''}\n\n"

    if title_analysis['too_short_titles']:
        report += f"🟢 LOW: {len(title_analysis['too_short_titles'])} offers with TOO SHORT TITLES\n"
        report += f"   Titles shorter than 10 characters\n"
        report += f"   Indices: {title_analysis['too_short_titles'][:10]}{'...' if len(title_analysis['too_short_titles']) > 10 else ''}\n\n"

    report += """
💡 RECOMMENDATIONS:
1. Focus on fixing EMPTY DATES first - these are critical for the travel offers
2. Then fix EMPTY PRICES - users need pricing information
3. Finally address EMPTY DESTINATIONS - improves search/filtering
4. Test fixes on a few examples before applying to all offers

"""

    # Show examples of problematic offers
    if any([date_analysis['empty_dates'], price_analysis['empty_prices'], destination_analysis['empty_destinations']]):
        report += "🔍 EXAMPLES OF PROBLEMATIC OFFERS:\n\n"

        examples_shown = 0
        for i, offer in enumerate(offers):
            has_issues = (
                i in date_analysis['empty_dates'] or
                i in price_analysis['empty_prices'] or
                i in destination_analysis['empty_destinations']
            )

            if has_issues and examples_shown < 5:
                report += f"Offer {i}:\n"
                report += f"  Title: {offer.get('title', 'MISSING')[:80]}\n"
                report += f"  Link: {offer.get('link', 'MISSING')[:80]}\n"
                report += f"  Price: {offer.get('price', 'MISSING')}\n"
                report += f"  Dates: {offer.get('dates', 'MISSING')}\n"
                report += f"  Destination: {offer.get('destination', 'MISSING')}\n"
                report += "\n"
                examples_shown += 1

    return report


def save_detailed_report(offers: List[Dict[str, Any]], report_text: str):
    """Save detailed analysis to a text file."""
    output_path = "dari_tour_data_analysis_report.txt"

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(report_text)

        # Add detailed breakdown
        f.write("\n" + "="*50 + "\n")
        f.write("DETAILED BREAKDOWN BY OFFER\n")
        f.write("="*50 + "\n\n")

        for i, offer in enumerate(offers):
            f.write(f"Offer {i}:\n")
            f.write(f"  Title: {offer.get('title', 'MISSING')}\n")
            f.write(f"  Link: {offer.get('link', 'MISSING')}\n")
            f.write(f"  Price: {offer.get('price', 'MISSING')}\n")
            f.write(f"  Dates: {offer.get('dates', 'MISSING')}\n")
            f.write(f"  Destination: {offer.get('destination', 'MISSING')}\n")
            f.write("\n")

    print(f"📄 Detailed report saved to: {output_path}")


def main():
    """Main analysis function."""
    json_path = "/home/dani/Desktop/Organizer/travel-comparator/dari_tour_scraped.json"

    offers = load_offers(json_path)
    if not offers:
        return

    report = generate_report(offers)
    print(report)

    save_detailed_report(offers, report)


if __name__ == "__main__":
    main()