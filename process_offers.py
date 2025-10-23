import json
import re
from datetime import datetime
from dateutil import parser as date_parser
import uuid
import os
import difflib

# Load destination mappings once
MAPPINGS = {}
try:
    mappings_file = os.path.join(os.path.dirname(__file__), 'destination_mappings.json')
    with open(mappings_file, 'r', encoding='utf-8') as f:
        MAPPINGS = json.load(f)
except FileNotFoundError:
    print("Warning: destination_mappings.json not found. Destination normalization will be limited.")
except json.JSONDecodeError:
    print("Warning: destination_mappings.json is invalid JSON. Destination normalization will be limited.")

# Exchange rates (approximate, update as needed)
BGN_TO_EUR = 0.511292981
USD_TO_EUR = 0.85

def parse_price(price_str, agency):
    """Parse price string to EUR."""
    price_str = price_str.strip()
    
    try:
        if agency == 'Angel Travel':
            # Format: "421.00 лв. / 215.25 EUR"
            match = re.search(r'(\d+\.?\d*)\s*лв\.?\s*/\s*(\d+\.?\d*)\s*EUR', price_str)
            if match:
                return float(match.group(2))
        else:
            # Format: "2343 лв." or similar, convert to EUR
            bgn_match = re.search(r'(\d+\.?\d*)\s*лв\.?', price_str)
            if bgn_match:
                bgn = float(bgn_match.group(1))
                return round(bgn * BGN_TO_EUR, 2)
            
            # Format: "50000$" or similar, convert USD to EUR
            usd_match = re.search(r'(\d+(?:\.\d+)?)\s*\$', price_str)
            if usd_match:
                usd = float(usd_match.group(1))
                return round(usd * USD_TO_EUR, 2)
    except Exception as e:
        print(f"Warning: Failed to parse price '{price_str}' for {agency}. Error: {e}")
        return None
        
    if price_str:
        print(f"Warning: Price string '{price_str}' for {agency} did not match any known format.")
        
    return None

def _infer_angel_travel_dates(title):
    """Infer dates for Angel Travel based on title keywords."""
    title_lower = title.lower()
    if 'нова година' in title_lower or 'new year' in title_lower:
        return '2025-12-31', '2026-01-01'
    elif 'коледа' in title_lower or 'christmas' in title_lower:
        return '2025-12-25', '2025-12-26'
    elif 'свети валентин' in title_lower or 'valentine' in title_lower:
        return '2026-02-14', None
    elif 'карнавал' in title_lower or 'carnival' in title_lower:
        return '2026-02-01', '2026-02-05'  # Approximate Venice Carnival dates
    return None, None

def _parse_date_string(date_str, agency, title):
    """Parse a date string, handling single dates, ranges, and multiple dates."""
    date_str = date_str.strip()
    
    # Handle already ISO formatted dates
    if re.match(r'\d{4}-\d{2}-\d{2}', date_str):
        if ' - ' in date_str:
            parts = date_str.split(' - ')
            try:
                start = parts[0].strip()
                end = parts[1].strip() if len(parts) > 1 and parts[1].strip() else None
                return start, end
            except:
                return date_str, None
        else:
            return date_str, None
    
    # Handle comma-separated multiple dates (take first one)
    if ',' in date_str:
        first_date = date_str.split(',')[0].strip()
        date_str = first_date
    
    # Handle DD.MM.YYYY format
    if ' - ' in date_str:
        parts = date_str.split(' - ')
        try:
            start = date_parser.parse(parts[0], dayfirst=True).date().isoformat()
            end = date_parser.parse(parts[1], dayfirst=True).date().isoformat() if len(parts) > 1 and parts[1].strip() else None
            return start, end
        except Exception as e:
            print(f"Warning: Failed to parse date range '{date_str}' for {agency} - {title}. Error: {e}")
            return None, None
    else:
        # Try to parse as single date
        try:
            start = date_parser.parse(date_str, dayfirst=True).date().isoformat()
            return start, None
        except Exception as e:
            print(f"Warning: Failed to parse single date '{date_str}' for {agency} - {title}. Error: {e}")
            return None, None

def parse_dates(dates_str, description, agency, title):
    """Parse dates to start and end ISO strings."""
    dates_str = dates_str.strip() if dates_str else ''
    description = description.strip() if description else ''

    # Try different sources based on agency
    if agency == 'Aratur' and description:
        # Aratur stores dates in description field
        dates_str = description
    elif agency == 'Dari Tour':
        # Dari Tour has dates in both fields, prefer the dates field if it exists
        if not dates_str and description:
            # Extract dates from description like "Дати: 09.02.2026, 20.02.2026"
            date_match = re.search(r'Дати:\s*([^,\n]+)', description)
            if date_match:
                dates_str = date_match.group(1).strip()

    # Angel Travel specific inference if dates_str is still empty
    if agency == 'Angel Travel' and not dates_str:
        start, end = _infer_angel_travel_dates(title)
        if start:
            return start, end

    if not dates_str:
        return None, None

    # General date string parsing
    return _parse_date_string(dates_str, agency, title)

def normalize_destination(dest, mappings):
    """Normalize destination names to standard English."""
    dest = dest.lower().strip()
    
    # Common prefixes to strip
    prefixes = ['oferti ', 'pochivki ', 'ekskurziya do ', 'po4ivki ']
    for prefix in prefixes:
        if dest.startswith(prefix):
            dest = dest[len(prefix):].strip()
            break
    
    # Exact match first
    if dest in mappings:
        return mappings[dest]
    
    # Substring match for partial matches
    for key, value in mappings.items():
        if key in dest or dest in key:
            return value
    
    # Fuzzy matching
    matches = difflib.get_close_matches(dest, mappings.keys(), n=1, cutoff=0.8)
    if matches:
        return mappings[matches[0]]
    
    # Fallback to title case
    return dest.title()

def parse_duration(duration_str, title, description, agency):
    """Parse duration to days (int)."""
    # First try the duration field
    if duration_str:
        match = re.search(r'(\d+)', duration_str)
        if match:
            days = int(match.group(1))
            # If it says "нощувки" (nights), convert to days (nights + 1)
            if 'нощув' in duration_str.lower():
                return days + 1
            return days
    
    # Try to extract from title
    if title:
        # Look for patterns like "3 нощувки", "5 дни", "4 nights", etc.
        night_match = re.search(r'(\d+)\s*нощув', title.lower())
        if night_match:
            return int(night_match.group(1)) + 1
        
        day_match = re.search(r'(\d+)\s*дни', title.lower())
        if day_match:
            return int(day_match.group(1))
        
        day_match_en = re.search(r'(\d+)\s*days?', title.lower())
        if day_match_en:
            return int(day_match_en.group(1))
    
    # Try to extract from description
    if description:
        night_match = re.search(r'(\d+)\s*нощув', description.lower())
        if night_match:
            return int(night_match.group(1)) + 1
        
        day_match = re.search(r'(\d+)\s*дни', description.lower())
        if day_match:
            return int(day_match.group(1))
    
    return None

def standardize_offer(offer, agency):
    """Standardize a single offer."""
    title = offer.get('title', '').strip()
    link = offer.get('link', '').strip()
    
    # Unified destination extraction: use 'destination' field if available, otherwise use 'title'
    raw_destination = offer.get('destination', '').strip() or title
    destination = normalize_destination(raw_destination, MAPPINGS)
    
    program_info = offer.get('program_info', '').strip()
    price_includes = offer.get('price_includes', []) if isinstance(offer.get('price_includes'), list) else []
    price_excludes = offer.get('price_excludes', []) if isinstance(offer.get('price_excludes'), list) else []
    hotel_titles = offer.get('hotel_titles', []) if isinstance(offer.get('hotel_titles'), list) else []
    booking_conditions = offer.get('booking_conditions', '').strip()
    scraped_at = offer.get('scrapedAt', '')

    price_eur = parse_price(offer.get('price', ''), agency)
    dates_start, dates_end = parse_dates(offer.get('dates', ''), offer.get('description', ''), agency, title)
    duration_days = parse_duration(offer.get('duration', ''), title, offer.get('description', ''), agency)

    return {
        'id': str(uuid.uuid4()),
        'agency': agency,
        'title': title,
        'destination': destination,
        'price_eur': price_eur,
        'dates_start': dates_start,
        'dates_end': dates_end,
        'duration_days': duration_days,
        'program_info': program_info,
        'price_includes': price_includes,
        'price_excludes': price_excludes,
        'hotel_titles': hotel_titles,
        'booking_conditions': booking_conditions,
        'link': link,
        'scraped_at': scraped_at
    }

def process_files(file_paths):
    """Process multiple JSON files and return unified list."""
    unified_offers = []
    agency_map = {
        'angel_travel_scrape.json': 'Angel Travel',
        'aratur.json': 'Aratur',
        'dari_tour_scraped.json': 'Dari Tour'
    }

    for file_path in file_paths:
        agency = agency_map.get(file_path.split('/')[-1], 'Unknown')
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            for offer in data:
                standardized = standardize_offer(offer, agency)
                unified_offers.append(standardized)
        except Exception as e:
            print(f"Error processing {file_path}: {e}")

    return unified_offers

if __name__ == '__main__':
    files = [
        '/home/dani/Desktop/Organizer/angel_travel_scrape.json',
        '/home/dani/Desktop/Organizer/aratur.json',
        '/home/dani/Desktop/Organizer/dari_tour_scraped.json'
    ]
    unified = process_files(files)
    with open('/home/dani/Desktop/Organizer/unified_offers.json', 'w', encoding='utf-8') as f:
        json.dump(unified, f, ensure_ascii=False, indent=2)
    print(f"Processed {len(unified)} offers into unified_offers.json")