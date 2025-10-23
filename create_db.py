import json
import sqlite3

def create_db():
    conn = sqlite3.connect('travel_offers.db')
    cursor = conn.cursor()

    # Create table
    cursor.execute('DROP TABLE IF EXISTS offers')
    cursor.execute('''
        CREATE TABLE offers (
            id TEXT PRIMARY KEY,
            agency TEXT,
            title TEXT,
            destination TEXT,
            price_eur REAL,
            dates_start TEXT,
            dates_end TEXT,
            duration_days INTEGER,
            program_info TEXT,
            price_includes TEXT,  -- JSON string
            price_excludes TEXT,  -- JSON string
            hotel_titles TEXT,    -- JSON string
            booking_conditions TEXT,
            link TEXT,
            scraped_at TEXT
        )
    ''')

    # Load unified data
    with open('unified_offers.json', 'r', encoding='utf-8') as f:
        offers = json.load(f)

    # Insert data
    for offer in offers:
        cursor.execute('''
            INSERT OR REPLACE INTO offers (
                id, agency, title, destination, price_eur,
                dates_start, dates_end, duration_days, program_info,
                price_includes, price_excludes, hotel_titles,
                booking_conditions, link, scraped_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            offer['id'], offer['agency'], offer['title'], offer['destination'],
            offer['price_eur'], offer['dates_start'], offer['dates_end'],
            offer['duration_days'], offer['program_info'],
            json.dumps(offer['price_includes']), json.dumps(offer['price_excludes']),
            json.dumps(offer['hotel_titles']), offer['booking_conditions'],
            offer['link'], offer['scraped_at']
        ))

    conn.commit()
    conn.close()
    print(f"Inserted {len(offers)} offers into database.")

if __name__ == '__main__':
    create_db()