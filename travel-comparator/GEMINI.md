# Project Context: travel-comparator

This project is a **Travel Offers Comparator**, designed to aggregate, display, and filter travel offers from various Bulgarian travel agencies.

## 1. Project Overview

| Aspect | Details |
| :--- | :--- |
| **Type** | Full-stack web application with a data scraping component. |
| **Frontend** | Next.js (v16), React (v19), TypeScript, Tailwind CSS. |
| **Styling** | Tailwind CSS is used for all styling, including a custom gradient theme. |
| **Data Flow** | Offers are scraped using a Python script and stored in a static JSON file (`public/data.json` or similar). The Next.js frontend loads this JSON file client-side for filtering and display. |
| **Data Scraping** | A dedicated Python script (`python/aratour_scraper.py`) uses `asyncio`, `aiohttp`, and `BeautifulSoup` to perform complex, asynchronous web scraping of travel agency websites (e.g., `aratour.bg`). |
| **Database** | The dependency `better-sqlite3` is present in `package.json`, suggesting potential future or current use of a local SQLite database, though the current data flow appears to rely on static JSON files. |

## 2. Key Commands and Workflow

### Frontend (Next.js)

The standard Next.js commands are used for development and production.

| Command | Description |
| :--- | :--- |
| `npm install` | Installs all Node.js dependencies. |
| `npm run dev` | Starts the development server on `http://localhost:3000`. |
| `npm run build` | Creates a production build of the application. |
| `npm run start` | Starts the Next.js production server. |
| `npm run lint` | Runs ESLint for code quality checks. |

### Data Scraping (Python)

The data is generated using a Python script. It is assumed a virtual environment (`python/.venv`) is used.

1.  **Activate Virtual Environment**: `source python/.venv/bin/activate`
2.  **Run Scraper**: `python python/aratour_scraper.py`
    *   *Note*: The scraper is complex and uses asynchronous networking. It outputs a simplified JSON file (e.g., `aratur.json` or updates `public/data.json`).

## 3. Core Files and Structure

| Path | Description |
| :--- | :--- |
| `app/page.tsx` | The main application page. Handles data fetching from `data.json`, client-side filtering, and view mode switching (Grid/Table). |
| `components/OfferCard.tsx` | React component for displaying a single offer in the Grid view. Heavily styled with Tailwind CSS. |
| `components/OfferRow.tsx` | (Inferred) React component for displaying a single offer in the Table view. |
| `public/data.json` | The static JSON file containing the scraped travel offer data, loaded by the frontend. |
| `python/aratour_scraper.py` | The primary Python script responsible for scraping travel offers from `aratour.bg`. |
| `dari_tour_scraped.json` | Another scraped data file, suggesting the project aggregates data from multiple sources. |
| `tailwind.config.ts` | Configuration for Tailwind CSS. |
| `next.config.ts` | Next.js configuration file. |

## 4. Development Conventions

*   **Framework**: Next.js App Router.
*   **Language**: TypeScript for the frontend.
*   **Styling**: Tailwind CSS is the sole styling framework. All components use utility classes.
*   **Data Structure**: Offers conform to the `Offer` interface defined in `app/page.tsx`, which includes detailed fields like `price_eur`, `dates_start`, `duration_days`, `program_info`, and `price_includes`/`price_excludes`.
*   **Filtering**: Filtering logic is implemented client-side in `app/page.tsx` using `useState` and `useMemo`.