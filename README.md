# Car Listing Service (FastAPI + PostgreSQL + Playwright)

A small end-to-end backend service that scrapes car listings from Facebook Marketplace, stores them in PostgreSQL, and exposes CRUD/refresh APIs. It demonstrates data ingestion, persistence, and API design with deduplication and idempotent refresh.

## Features

- Scraper (Playwright):
  - Fetches multiple listings from a Facebook Marketplace URL.
  - Extracts: title, price, currency, year, mileage, location (+ url, raw_json snippet).
  - Infinite-scroll scraping (capped), optional cookies support.
  - Idempotent re-runs via upsert (no duplicates).

- Data Store (PostgreSQL):
  - SQLAlchemy model `Listing` with unique `listing_id`.
  - Indexed on `price`, `year`.
  - Tables auto-create on app startup.

- Web Server (FastAPI):
  - Health: `GET /health`.
  - Trigger scrape: `POST /scrape`.
  - List: `GET /listings` with pagination and filters.
  - Get one: `GET /listings/{listing_id}`.
  - Update: `PATCH /listings/{listing_id}`.
  - Delete: `DELETE /listings/{listing_id}`.

## Project Layout

```
app/
  api/routes.py        # FastAPI routes
  crud.py              # CRUD + upsert on conflict
  db.py                # Engine/session setup (reads .env)
  main.py              # FastAPI app + startup table creation
  models.py            # SQLAlchemy models
  schemas.py           # Pydantic schemas
  scrape.py            # Playwright scraper
  scheduler.py         # Optional hourly scrape via APScheduler
  utils.py             # Logger + retry helper
requirements.txt
```

## Requirements

- Windows, macOS, or Linux
- Python 3.12+
- PostgreSQL database (Aiven or local)
- Playwright browsers installed (Chromium)

Note: This repo includes a `venv` folder. If creating your own venv, ensure dependencies from `requirements.txt` are installed.

## Environment Variables (.env)

Create a `.env` in the project root. Example:

```
# --- Database connection (Aiven PostgreSQL) ---
POSTGRES_URL=postgres://USER:PASSWORD@HOST:PORT/defaultdb?sslmode=require

# Scraping target URL
TARGET_URL=https://www.facebook.com/marketplace/manila/cars?minPrice=350000

# Run scraper headless in CI/servers (1 = headless, 0 = headed)
HEADLESS=1

# Optional: Facebook cookies for better results (path relative to project root)
PLAYWRIGHT_COOKIES_FILE=./cookies.json

# Logging and DB pool tuning
LOG_LEVEL=INFO
DB_POOL_SIZE=5
DB_MAX_OVERFLOW=10

# Optional: cap for number of items collected in a run
SCRAPE_MAX_ITEMS=200
```

Notes:
- The code normalizes `postgres://` to `postgresql+psycopg2://` for SQLAlchemy.
- Aiven connections require `sslmode=require`.

## Setup

1) Install Playwright browsers (Chromium) in this project's venv:

Windows PowerShell:
```
C:\Users\HP\OneDrive\Desktop\projects\OnelotTask\venv\Scripts\playwright.exe install chromium
```

2) Run the API server (using venv):
```
C:\Users\HP\OneDrive\Desktop\projects\OnelotTask\venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8001
```

3) Health check:
```
curl http://127.0.0.1:8001/health
# {"status":"ok"}
```

## API Usage

Base URL: `http://127.0.0.1:8001`

- Trigger scrape
  - `POST /scrape`
  - Response: `{ "status": "ok" }`

- List listings (filters optional)
  - `GET /listings?skip=0&limit=50&min_price=400000&max_price=2000000&min_year=2018&location=Manila`
  - Response: JSON array of listings

- Get one
  - `GET /listings/{listing_id}`

- Update
  - `PATCH /listings/{listing_id}` with JSON body (any subset):
    ```json
    {
      "title": "Updated title",
      "price": 575000,
      "year": 2020,
      "mileage": 42000,
      "location": "Makati"
    }
    ```

- Delete
  - `DELETE /listings/{listing_id}`

### Postman Quick Start

- Base URL variable: `{{baseUrl}} = http://127.0.0.1:8001`
- Add requests:
  - GET `{{baseUrl}}/health`
  - POST `{{baseUrl}}/scrape`
  - GET `{{baseUrl}}/listings`
  - GET `{{baseUrl}}/listings/{listing_id}`
  - PATCH `{{baseUrl}}/listings/{listing_id}` (Body → raw JSON)
  - DELETE `{{baseUrl}}/listings/{listing_id}`

## How Deduplication and Refresh Work

- Each listing gets a stable `listing_id` derived from its URL (e.g., `/item/{id}`).
- The database has a unique constraint on `listing_id`.
- Ingestion uses a PostgreSQL `INSERT ... ON CONFLICT (listing_id) DO UPDATE` upsert:
  - If new: insert
  - If existing: update fields and set `updated_at` and `last_seen_at` to current time
- Re-running the scraper will therefore refresh rows, not create duplicates.

## Data Model

`Listing` fields:
- `id` (PK)
- `listing_id` (unique, indexed)
- `title`
- `price` (numeric)
- `currency` (text)
- `year` (int)
- `mileage` (int)
- `location` (text)
- `url` (text)
- `raw_json` (JSONB) — small HTML snippet for debugging
- `created_at`, `updated_at`, `last_seen_at` (timestamps)

Indexes: `price`, `year` for basic range queries.

## Scheduler (optional)

`app/scheduler.py` starts an hourly background job using APScheduler to run `scrape_marketplace`. This is imported by `app/main.py` so the scheduler starts with the app. Adjust or disable as needed in production.

## Verifying Data

- API:
  - `GET /listings?limit=10` to view sample rows
  - Re-run `POST /scrape` and fetch again; `updated_at`/`last_seen_at` should advance

- Aiven Console:
  - Open your PostgreSQL service → Query tab:
    - `SELECT COUNT(*) FROM listings;`
    - `SELECT id, listing_id, title, price, year, mileage, location FROM listings ORDER BY id DESC LIMIT 10;`

- Python one-liner (no psql):
```
C:\Users\HP\OneDrive\Desktop\projects\OnelotTask\venv\Scripts\python.exe - << 'PY'
import os
from sqlalchemy import create_engine, text
url=os.getenv('POSTGRES_URL','').replace('postgres://','postgresql+psycopg2://',1)
e=create_engine(url)
with e.connect() as c:
    print('count=', c.execute(text('SELECT COUNT(*) FROM listings')).scalar())
    for r in c.execute(text('SELECT id, listing_id, title, price FROM listings ORDER BY id DESC LIMIT 5')):
        print(r)
PY
```

## Troubleshooting

- Playwright missing browser:
  - Run: `playwright install chromium`.

- PowerShell quoting errors with ampersands (&):
  - Wrap URLs in single quotes or as environment variables in `.env`.

- SQLAlchemy `Can't load plugin: sqlalchemy.dialects:postgres`:
  - Ensure URL uses `postgresql+psycopg2://` (the app auto-normalizes `postgres://`).

- Fewer items than expected:
  - Facebook lazy-loads listings. The scraper scrolls until no new items appear with a configurable cap `SCRAPE_MAX_ITEMS`.
  - Add `cookies.json` if listings are gated by login/geo/age.

## Notes and Ethics

- Scraping Facebook content is subject to their Terms of Service. Use responsibly, only for allowed purposes, and avoid aggressive crawling.
- Consider adding backoff, request budgets, and proper consent where applicable.

## Tests

- Minimal test in `tests/test_crud.py` exercises upsert and retrieval against the configured DB. Extend with mocks/local DB for full coverage.

## License

For interview/demo purposes. Replace or add a proper OSS license for broader use.
