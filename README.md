# Travel Offers Comparator

A comprehensive web application for comparing travel offers from multiple Bulgarian travel agencies. This project scrapes, processes, and displays travel offers from Angel Travel, Aratur, and Dari Tour in a unified, comparable format.

## Features

- **Multi-Agency Comparison**: Compare offers from Angel Travel, Aratur, and Dari Tour side-by-side
- **Real-time Filtering**: Filter offers by destination, price range, and dates with instant results
- **Unified Data Format**: All offers standardized with consistent pricing (EUR), dates, and destinations
- **Responsive Design**: Clean, modern interface that works on desktop and mobile
- **Table & Grid Views**: Switch between spreadsheet-style table view and card grid view
- **Currency Conversion**: Automatic conversion from BGN and USD to EUR
- **Data Processing**: Robust parsing of travel offer data with fuzzy matching for destinations

## Project Structure

```
Organizer/
├── process_offers.py          # Data processing and standardization
├── create_db.py              # SQLite database creation
├── unified_offers.json       # Processed offer data
├── destination_mappings.json # Destination name mappings
├── travel_offers.db          # SQLite database
├── travel-comparator/        # Next.js web application
│   ├── app/
│   │   ├── api/offers/       # API routes for data fetching
│   │   ├── page.tsx          # Main application page
│   │   └── layout.tsx        # App layout
│   ├── components/           # React components
│   │   ├── OfferCard.tsx     # Grid view card component
│   │   └── OfferRow.tsx      # Table view row component
│   └── public/               # Static assets
└── *.json                    # Raw scraped data files
```

## Technology Stack

- **Backend Processing**: Python 3 with SQLite
- **Frontend**: Next.js 16 with TypeScript and Tailwind CSS
- **Database**: SQLite with better-sqlite3
- **Data Processing**: dateutil, regex, difflib for fuzzy matching
- **Styling**: Tailwind CSS with responsive design

## Data Sources

- **Angel Travel**: angel_travel_scrape.json
- **Aratur**: aratur.json
- **Dari Tour**: dari_tour_scraped.json

## Setup & Installation

### Prerequisites
- Python 3.8+
- Node.js 18+
- npm or yarn

### Backend Setup
```bash
# Install Python dependencies
pip install -r requirements.txt

# Process the scraped data
python3 process_offers.py

# Create the database
python3 create_db.py
```

### Frontend Setup
```bash
cd travel-comparator
npm install
npm run dev
```

The application will be available at `http://localhost:3000`

## Data Processing Pipeline

1. **Scraping**: Raw data collected from travel agency websites
2. **Processing**: `process_offers.py` standardizes all offers:
   - Currency conversion (BGN/USD → EUR)
   - Date parsing and normalization
   - Destination name standardization
   - Duration extraction from titles/descriptions
3. **Database**: SQLite database created with unified schema
4. **API**: Next.js API routes serve filtered data
5. **Frontend**: React components display offers in table/grid views

## Key Features

### Currency Conversion
- BGN to EUR: 0.511292981 exchange rate
- USD to EUR: 0.85 exchange rate
- Automatic detection and conversion

### Destination Normalization
- Fuzzy matching for destination names
- External JSON mapping file for custom mappings
- Prefix stripping (removes "oferti", "pochivki", etc.)

### Date Parsing
- Handles multiple date formats (DD.MM.YYYY, ISO, etc.)
- Comma-separated dates (takes first date)
- Agency-specific date extraction logic

### Duration Extraction
- Parses duration from dedicated fields
- Extracts from titles ("3 нощувки" = 4 days)
- Extracts from descriptions
- Handles Bulgarian and English text

## API Endpoints

- `GET /api/offers` - Fetch filtered offers
  - Query parameters: `destination`, `min_price`, `max_price`, `start_date`, `end_date`

## Development

### Adding New Agencies
1. Add scraper output to root directory
2. Update `agency_map` in `process_offers.py`
3. Update `files` list in `process_offers.py`
4. Re-run processing pipeline

### Updating Exchange Rates
Edit the constants in `process_offers.py`:
```python
BGN_TO_EUR = 0.511292981
USD_TO_EUR = 0.85
```

### Custom Destination Mappings
Edit `destination_mappings.json` to add custom mappings:
```json
{
  "sofia": "Sofia",
  "plovdiv": "Plovdiv"
}
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Future Enhancements

- Integration with ScrapeMate for automated data refresh
- User accounts and saved searches
- Price alerts and notifications
- Advanced filtering options
- Export functionality
- Mobile app companion