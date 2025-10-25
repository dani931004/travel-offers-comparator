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
                dates_start, dates_end, duration_days,
                link, scraped_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            offer['id'], offer['agency'], offer['title'], offer['destination'],
            offer['price_eur'], offer['dates_start'], offer['dates_end'],
            offer['duration_days'], offer['link'], offer['scraped_at']
        ))

    conn.commit()
    conn.close()
    print(f"Inserted {len(offers)} offers into database.")

if __name__ == '__main__':
    create_db()