# Copilot Instructions for Travel Offers Comparator

## Overview

This project compares travel offers from multiple Bulgarian travel agencies by scraping, processing, and displaying them in a unified web app. It consists of a Python backend for data processing and a Next.js frontend for visualization.

## Architecture

- **Backend (Python)**
  - Scraper outputs: `angel_travel_scrape.json`, `aratur.json`, `dari_tour_scraped.json`
  - Data processing: `process_offers.py` (currency conversion, date/destination normalization, duration extraction)
  - Database creation: `create_db.py` (SQLite, unified schema)
  - Mappings: `destination_mappings.json` (custom destination normalization)
  - Output: `unified_offers.json`, `travel_offers.db`

- **Frontend (Next.js)**
  - Located in `travel-comparator/`
  - Main page: `app/page.tsx`
  - API routes: `app/api/offers/`
  - Components: `components/OfferCard.tsx`, `components/OfferRow.tsx`
  - Static assets: `public/data.json`
  - Styling: Tailwind CSS

## Developer Workflows

- **Backend**
  - Install dependencies: `pip install -r requirements.txt`
  - Process data: `python3 process_offers.py`
  - Create DB: `python3 create_db.py`

- **Frontend**
  - Install dependencies: `cd travel-comparator && npm install`
  - Run dev server: `npm run dev` (http://localhost:3000)

## Data Processing Patterns

- Currency conversion rates are hardcoded in `process_offers.py`
- Dates are parsed from multiple formats; agency-specific logic is present
- Destinations normalized via fuzzy matching and external mapping file
- Duration extracted from titles/descriptions, supports Bulgarian/English

## Extending Functionality

- To add a new agency:
  1. Place scraper output in root
  2. Update `agency_map` and `files` in `process_offers.py`
  3. Re-run processing pipeline

- To update exchange rates or destination mappings, edit constants in `process_offers.py` and `destination_mappings.json`

## API

- Main endpoint: `GET /api/offers` (supports filtering by destination, price, date)

## Conventions

- All prices are converted to EUR
- Dates are normalized to a standard format
- Unified schema for offers in both JSON and SQLite

## Key Files & Directories

- `process_offers.py`, `create_db.py`, `destination_mappings.json`
- `travel-comparator/app/`, `travel-comparator/components/`
- `unified_offers.json`, `travel_offers.db`
