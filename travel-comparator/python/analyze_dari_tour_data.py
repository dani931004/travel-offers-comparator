#!/usr/bin/env python3
"""
Dari Tour Data Analyzer
Analyzes the quality of scraped Dari Tour data
"""

import json
import re
from datetime import datetime
from pathlib import Path

def load_data(file_path):
    """Load JSON data from file"""
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)

def analyze_offer_dates(offers):
    """Analyze date validity"""
    valid_dates = 0
    total_dates = 0

    for offer in offers:
        dates = offer.get('dates', '')
        if dates:
            total_dates += 1
            # Check if dates contain valid date patterns
            date_patterns = [
                r'\d{1,2}\.\d{1,2}\.\d{4}',  # DD.MM.YYYY
                r'\d{1,2}/\d{1,2}/\d{4}',    # DD/MM/YYYY
                r'\d{4}-\d{1,2}-\d{1,2}',    # YYYY-MM-DD
                r'\d{1,2}\s+(?:ян|фев|мар|апр|май|юни|юли|авг|сеп|окт|ноем|дек)',  # Bulgarian months
                r'\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)',  # English months
            ]

            if any(re.search(pattern, dates, re.IGNORECASE) for pattern in date_patterns):
                valid_dates += 1

    return valid_dates, total_dates

def analyze_offer_prices(offers):
    """Analyze price validity"""
    valid_prices = 0
    total_prices = 0

    for offer in offers:
        price = offer.get('price', '')
        if price:
            total_prices += 1
            # Check for valid price patterns (numbers with currency symbols)
            price_patterns = [
                r'\d+(?:,\d{3})*(?:\.\d{2})?\s*(?:лв|€|EUR|BGN|USD|\$)',  # Bulgarian/English currencies
                r'\d+(?:\.\d{3})*(?:,\d{2})?\s*(?:лв|€|EUR|BGN|USD|\$)',  # Alternative format
            ]

            if any(re.search(pattern, price, re.IGNORECASE) for pattern in price_patterns):
                valid_prices += 1

    return valid_prices, total_prices

def analyze_offer_destinations(offers):
    """Analyze destination validity"""
    # Known destinations in Bulgarian
    known_destinations = {
        'австралия', 'австрия', 'албания', 'аржентина', 'бали', 'белгия', 'босна и херцеговина',
        'ботсвана', 'бразилия', 'великобритания', 'виетнам', 'германия', 'гърция', 'дания',
        'доминиканска република', 'доминикана', 'дубай', 'египет', 'израел', 'индия', 'индонезия', 'испания',
        'италия', 'йордания', 'кабо верде', 'каймани', 'камбоджа', 'канада', 'кенія', 'кенія', 'кения', 'кипр',
        'кипър', 'китай', 'колумбия', 'коста рика', 'куба', 'лаос', 'малдиви', 'малайзия', 'малта',
        'мароко', 'мавриций', 'мексико', 'непал', 'нидерландия', 'нова зеландия', 'норвегия',
        'остров бали', 'панама', 'патагония', 'перу', 'полша', 'португалия', 'република южна африка',
        'русия', 'сейшели', 'сингапур', 'сирия', 'словения', 'сърбия', 'сащ', 'тайланд', 'тунис',
        'турция', 'узбекистан', 'украйна', 'филипини', 'финландия', 'франция', 'холандия',
        'хърватия', 'черна гора', 'чехия', 'чили', 'швейцария', 'шри ланка', 'юар', 'япония',
        'зимбабве', 'зanzibar', 'исландия', 'оае', 'унгария', 'islandия', 'oae', 'sasht', 'velikobritaniya', 'botsvana',
        'cherna-gora', 'dominikanska-republika', 'kitay', 'kostarika', 'meksiko', 'nepal',
        'novazelandiya', 'panama', 'patagoniya', 'portugaliya', 'republika-yuzhna-afrika',
        'shri-lanka', 'tayland', 'uzbekistan', 'velikobritaniya', 'yaponiya', 'zimbabve',
        'avstraliya', 'avstriya', 'bali', 'belgiya', 'bosna-i-hertsegovina', 'braziliya',
        'chehiya', 'chili', 'daniya', 'dubay', 'egipet', 'filipini', 'frantsiya', 'germaniya',
        'hrvatska', 'indiya', 'indoneziya', 'ispaniya', 'italiya', 'kambodzha', 'kanada',
        'keniya', 'kolumbiya', 'kuba', 'malayziya', 'maldivi', 'maroko', 'mavritsiy', 'niderlandiya',
        'polsha', 'rusiya', 'singapur', 'suriya', 'shveytsariya', 'tunis', 'turtsiya', 'ungariya',
        'arzhentina', 'islandiya', 'oae', 'sasht'
    }

    valid_destinations = 0
    total_destinations = 0

    for offer in offers:
        destination = offer.get('destination', '').strip().lower()
        if destination:
            total_destinations += 1
            # Check if destination is in known list
            if destination in known_destinations:
                valid_destinations += 1

    return valid_destinations, total_destinations

def analyze_offer_titles(offers):
    """Analyze title validity"""
    valid_titles = 0
    total_titles = 0

    for offer in offers:
        title = offer.get('title', '').strip()
        if title:
            total_titles += 1
            # Title should be non-empty and not just whitespace
            if len(title) > 5:  # Reasonable minimum length
                valid_titles += 1

    return valid_titles, total_titles

def analyze_offer_links(offers):
    """Analyze link validity"""
    valid_links = 0
    total_links = 0

    for offer in offers:
        link = offer.get('link', '').strip()
        if link:
            total_links += 1
            # Check if it's a valid URL
            if link.startswith('http') and 'dari-tour.com' in link:
                valid_links += 1

    return valid_links, total_links

def generate_report(offers):
    """Generate comprehensive data quality report"""
    print("=== DARI TOUR DATA QUALITY ANALYSIS ===")
    print(f"Total offers analyzed: {len(offers)}")
    print()

    # Analyze each field
    analyses = [
        ("Dates", analyze_offer_dates),
        ("Prices", analyze_offer_prices),
        ("Destinations", analyze_offer_destinations),
        ("Titles", analyze_offer_titles),
        ("Links", analyze_offer_links),
    ]

    for field_name, analyzer_func in analyses:
        valid, total = analyzer_func(offers)
        percentage = (valid / total * 100) if total > 0 else 0
        print(f"{field_name}: {valid}/{total} ({percentage:.1f}%)")

    print()
    print("=== SAMPLE OFFERS ===")

    # Show first 5 offers as samples
    for i, offer in enumerate(offers[:5]):
        print(f"\nOffer {i+1}:")
        print(f"  Title: {offer.get('title', 'N/A')}")
        print(f"  Destination: {offer.get('destination', 'N/A')}")
        print(f"  Price: {offer.get('price', 'N/A')}")
        print(f"  Dates: {offer.get('dates', 'N/A')}")
        print(f"  Link: {offer.get('link', 'N/A')}")

def main():
    """Main function"""
    data_file = Path("/home/dani/Desktop/Organizer/travel-comparator/dari_tour_scraped.json")

    if not data_file.exists():
        print(f"Error: Data file not found: {data_file}")
        return

    print(f"Loading data from: {data_file}")
    offers = load_data(data_file)

    if not offers:
        print("Error: No offers found in data file")
        return

    generate_report(offers)

if __name__ == "__main__":
    main()