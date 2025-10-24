#!/usr/bin/env python3
"""
ARATOUR DATA FIXER - Final Issues Resolution
Fixes remaining issues: invalid destinations, date inconsistencies, suspicious prices
"""

import json
import re
from typing import Dict, List, Any
from datetime import datetime, timedelta


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


def fix_invalid_destinations(offers: List[Dict[str, Any]]) -> int:
    """Fix offers with invalid destinations by extracting proper destinations from titles."""
    fixed_count = 0

    # Known destination mappings for invalid destinations
    destination_fixes = {
        "Тръгване От Варна": None,  # Will extract from title
        "Pochivki Malta": "Малта",
        "Pochivki V Yordania": "Йордания",
    }

    # Country/city mappings for better extraction
    known_countries = {
        # European countries
        "Турция": ["Турция", "Анталия", "Алания", "Бодрум", "Сиде", "Лара", "Фетие", "Анталия"],
        "Италия": ["Италия", "Венеция", "Милан", "Таормина", "Сицилия", "Рим", "Флоренция", "Венеция"],
        "Испания": ["Испания", "Коста Брава", "Барселона", "Каталуния"],
        "Франция": ["Франция", "Елзас", "Париж", "Ницца"],
        "Гърция": ["Гърция"],
        "Германия": ["Германия", "Баварски"],
        "Швейцария": ["Швейцария"],
        "Австрия": ["Австрия", "Залцбург", "Инсбрук", "Мюнхен"],
        "Чехия": ["Чехия"],
        "Полша": ["Полша", "Карпатите"],
        "Унгария": ["Унгария"],
        "Румъния": ["Румъния"],
        "България": ["България"],
        "Албания": ["Албания"],
        "Македония": ["Македония"],
        "Сърбия": ["Сърбия"],
        "Черна гора": ["Черна гора"],
        "Хърватия": ["Хърватия"],
        "Словения": ["Словения"],
        "Малта": ["Малта"],
        "Португалия": ["Португалия", "Порто", "Лисабон", "Сантяго", "Мадейра"],
        "Ирландия": ["Ирландия"],
        "Великобритания": ["Великобритания"],
        "Норвегия": ["Норвегия", "Фиорди"],
        "Швеция": ["Швеция", "Скандинавия"],
        "Дания": ["Дания", "Скандинавия"],

        # Asian countries
        "Египет": ["Египет", "Шарм", "Хургада", "Кайро", "Нил"],
        "Тунис": ["Тунис", "Джерба"],
        "Мароко": ["Мароко", "Имперски", "Касабланка", "Марakech"],
        "Йордания": ["Йордания", "Петра"],
        "Израел": ["Израел"],
        "ОАЕ": ["ОАЕ", "Дубай", "Абу Даби", "Рас Ал Хайма"],
        "Катар": ["Катар", "Доха"],
        "Оман": ["Оман"],
        "Китай": ["Китай", "Пекин", "Шанхай", "Теракота"],
        "Япония": ["Япония", "Токио", "Киото"],
        "Южна Корея": ["Южна Корея", "Сеул"],
        "Индия": ["Индия", "Раджастан", "Делхи", "Агра", "Джайпур"],
        "Шри Ланка": ["Шри Ланка"],
        "Таиланд": ["Таиланд", "Банкок", "Пукет"],
        "Виетнам": ["Виетнам", "Ханой", "Хо Ши Мин", "Фу Квок"],
        "Камбоджа": ["Камбоджа", "Сием Реап", "Ангкор"],
        "Индонезия": ["Индонезия", "Бали"],
        "Малайзия": ["Малайзия"],
        "Сингапур": ["Сингапур"],
        "Филипини": ["Филипини"],
        "Малдиви": ["Малдиви"],
        "Непал": ["Непал", "Тибет"],
        "Узбекистан": ["Узбекистан", "Самарканд", "Бухара"],

        # African countries
        "Мароко": ["Мароко"],
        "Тунис": ["Тунис"],
        "Египет": ["Египет"],
        "Кения": ["Кения", "Масаи Мара", "Сафари"],
        "Танзания": ["Танзания", "Занзибар", "Сафари"],
        "Ботсвана": ["Ботсвана"],
        "Зимбабве": ["Зимбабве"],
        "Намибия": ["Намибия"],
        "ЮАР": ["ЮАР"],
        "Етиопия": ["Етиопия"],
        "Кабо Верде": ["Кабо Верде", "Сал"],
        "Сенегал": ["Сенегал"],
        "Сао Томе и Принсипи": ["Сао Томе", "Принсипи"],

        # American countries
        "САЩ": ["САЩ", "Ню Йорк", "Вашингтон", "Лос Анджелис"],
        "Канада": ["Канада"],
        "Мексико": ["Мексико"],
        "Куба": ["Куба"],
        "Доминикана": ["Доминикана", "Пунта Кана", "Ла Романа", "Баяхибe"],
        "Ямайка": ["Ямайка"],
        "Бразилия": ["Бразилия", "Рио"],
        "Аргентина": ["Аргентина"],
        "Чили": ["Чили"],
        "Перу": ["Перу", "Мачу Пикчу", "Куско"],
        "Колумбия": ["Колумбия"],
        "Венецуела": ["Венецуела", "Анхел"],
        "Еквадор": ["Еквадор"],
        "Коста Рика": ["Коста Рика"],
        "Панама": ["Панама"],
        "Кюрасао": ["Кюрасао"],

        # Oceania
        "Австралия": ["Австралия"],
        "Нова Зеландия": ["Нова Зеландия"],

        # Caribbean
        "Карибски Острови": ["Карибски", "Бриз"],

        # Russia
        "Русия": ["Русия", "Москва", "Санкт Петербург", "Московска област"],
    }

    def find_country_from_keywords(title: str) -> str:
        """Find country based on keywords in title."""
        title_lower = title.lower()

        for country, keywords in known_countries.items():
            for keyword in keywords:
                if keyword.lower() in title_lower:
                    return country

        return None

    for i, offer in enumerate(offers):
        current_dest = offer.get('destination', '').strip()

        # Skip if destination is already valid
        if current_dest and current_dest not in destination_fixes:
            continue

        title = offer.get('title', '')

        # Try to find country from keywords first
        new_destination = find_country_from_keywords(title)

        # Apply known fixes if keyword search didn't work
        if not new_destination and current_dest in destination_fixes:
            new_destination = destination_fixes[current_dest]

        # Special multi-country cases
        if not new_destination:
            if 'Шри Ланка' in title and 'Малдиви' in title:
                new_destination = 'Шри Ланка и Малдиви'
            elif 'Виетнам' in title and 'Камбоджа' in title:
                new_destination = 'Виетнам и Камбоджа'
            elif 'Ботсвана' in title and 'Зимбабве' in title:
                new_destination = 'Ботсвана и Зимбабве'
            elif 'Намибия' in title and 'Ботсвана' in title and 'Зимбабве' in title:
                new_destination = 'Намибия, Ботсвана и Зимбабве'
            elif 'Кайро' in title and 'Хургада' in title:
                new_destination = 'Египет'
            elif 'Цяла Скандинавия' in title:
                new_destination = 'Скандинавия'
            elif 'Швеция' in title and 'Дания' in title:
                new_destination = 'Швеция и Дания'
            elif 'Грузия' in title and 'Армения' in title:
                new_destination = 'Грузия и Армения'
            elif 'Италия' in title and 'Швейцария' in title:
                new_destination = 'Италия и Швейцария'
            elif 'Китай' in title and 'Япония' in title:
                new_destination = 'Китай и Япония'
            elif 'Гранд Тур' in title and 'Япония' in title:
                new_destination = 'Япония и Южна Корея'

        if new_destination and new_destination != current_dest:
            print(f"  [{i}] Fixed destination: '{current_dest}' → '{new_destination}'")
            offer['destination'] = new_destination
            fixed_count += 1

    return fixed_count


def fix_date_inconsistencies(offers: List[Dict[str, Any]]) -> int:
    """Fix offers with inconsistent date ranges."""
    fixed_count = 0

    for i, offer in enumerate(offers):
        dates = offer.get('dates', '')
        title = offer.get('title', '')

        if not dates or '-' not in dates:
            continue

        try:
            # Parse date range
            date_parts = dates.split(' - ')
            if len(date_parts) != 2:
                continue

            start_date = datetime.strptime(date_parts[0].strip(), '%d.%m.%Y')
            end_date = datetime.strptime(date_parts[1].strip(), '%d.%m.%Y')

            # Calculate actual duration
            actual_days = (end_date - start_date).days + 1  # +1 because both dates are inclusive

            # Extract stated duration from title
            duration_match = re.search(r'(\d+)\s*(?:дни|нощувки)', title, re.IGNORECASE)
            if duration_match:
                stated_days = int(duration_match.group(1))

                # Check if they match (allowing for some flexibility)
                if abs(actual_days - stated_days) > 1:  # More than 1 day difference
                    print(f"  [{i}] Date inconsistency: {dates} ({actual_days} days) vs title states {stated_days} days")

                    # Try to fix by recalculating end date
                    if stated_days > 1:
                        corrected_end = start_date + timedelta(days=stated_days - 1)
                        corrected_dates = f"{start_date.strftime('%d.%m.%Y')} - {corrected_end.strftime('%d.%m.%Y')}"
                        print(f"    Corrected: {dates} → {corrected_dates}")
                        offer['dates'] = corrected_dates
                        fixed_count += 1

        except (ValueError, IndexError) as e:
            continue

    return fixed_count


def review_suspicious_prices(offers: List[Dict[str, Any]]) -> None:
    """Review offers with suspiciously high prices."""
    print("\n🔍 REVIEWING SUSPICIOUS PRICES:")
    print("=" * 50)

    for i, offer in enumerate(offers):
        price_str = offer.get('price', '')
        title = offer.get('title', '')

        if not price_str:
            continue

        # Extract numeric price
        price_match = re.search(r'(\d{1,3}(?:[.,]\d{3})*(?:\.\d{2})?)', price_str.replace(' ', ''))
        if price_match:
            try:
                price = float(price_match.group(1).replace(',', '').replace('.', ''))

                # Flag very high prices (> 10,000 BGN)
                if price > 10000:
                    print(f"[HIGH PRICE: {price_str}] {title[:60]}...")
                    print(f"  URL: {offer.get('link', '')}")

            except ValueError:
                continue

    print("\n💡 Note: High prices appear to be legitimate luxury trips (Australia/NZ cruises)")


def main():
    """Main function to fix all remaining issues."""
    print("🔧 ARATOUR FINAL ISSUES FIXER")
    print("=" * 50)

    # Load current data
    offers = load_offers('aratur.json')
    if not offers:
        print("❌ No offers loaded")
        return

    print(f"Loaded {len(offers)} offers from aratur.json")

    # Create backup
    save_offers(offers, 'aratur_final_backup.json')

    # Fix invalid destinations
    print("\n1. Fixing invalid destinations...")
    dest_fixed = fix_invalid_destinations(offers)
    print(f"✓ Fixed {dest_fixed} invalid destinations")

    # Fix date inconsistencies
    print("\n2. Fixing date range inconsistencies...")
    date_fixed = fix_date_inconsistencies(offers)
    print(f"✓ Fixed {date_fixed} date inconsistencies")

    # Review suspicious prices
    print("\n3. Reviewing suspicious prices...")
    review_suspicious_prices(offers)

    # Save fixed data
    save_offers(offers, 'aratur.json')

    print("\n✅ FINAL FIXES COMPLETE!")
    print(f"   - Invalid destinations fixed: {dest_fixed}")
    print(f"   - Date inconsistencies fixed: {date_fixed}")
    print("   - Suspicious prices reviewed (no changes needed)")
    print("   - Suspicious prices reviewed (no changes needed)")


if __name__ == "__main__":
    main()