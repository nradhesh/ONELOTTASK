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
  - List: `GET /listings` with pagination and filtes.
  - Get one: `GET /listings/{listing_id}`.
  - Update: `PATCH /listings/{listing_id}`.
  - Delete: `DELETE /listings/{listing_id}`.
##Screenshots
<img width="1915" height="489" alt="image" src="https://github.com/user-attachments/assets/77769794-8f93-424b-9a88-e557c97d1ebd" />
### Web Routes tesing via Postman
<img width="1503" height="872" alt="image" src="https://github.com/user-attachments/assets/fee17aeb-2e8e-4983-83b3-612e8bf66c1e" />
### Request handling and rendering via server
<img width="1244" height="533" alt="image" src="https://github.com/user-attachments/assets/1842f94f-0ed9-4905-83bd-156aeb65a666" />


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
{your path}\venv\Scripts\playwright.exe install chromium
```

2) Run the API server (using venv):
```
{your path}\venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

3) Health check:
```
curl http://127.0.0.1:8000/health
# {"status":"ok"}
```

## How to Run the Project

- Activate the venv (if not already):
  - PowerShell:
    ```powershell
    {your path}\venv\Scripts\Activate.ps1
    ```

- Ensure `.env` is populated (see above). Optional: place `cookies.json` at project root if scraping gated content.

- Install Playwright browsers (one-time):
  ```powershell
  {your path}\venv\Scripts\playwright.exe install chromium
  ```

- Start the API:
  ```powershell
  {your path}\venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
  ```

- Trigger a scrape (new terminal):
  ```powershell
  Invoke-WebRequest -UseBasicParsing -Method Post http://127.0.0.1:8000/scrape
  ```

- Verify data via API:
  ```powershell
  (Invoke-WebRequest -UseBasicParsing http://127.0.0.1:8000/listings?limit=10).Content | ConvertFrom-Json | Format-List
  ```

- Verify in Aiven Console (GUI): Query tab
  ```sql
  SELECT COUNT(*) FROM listings;
  SELECT id, listing_id, title, price, year, mileage, location FROM listings ORDER BY id DESC LIMIT 10;
  ```

## API Usage

Base URL: `http://127.0.0.1:8000`

- Trigger scrape
  - `POST /scrape`
  - Response: `{ "status": "ok" }`

- List listings (filters optional)
  - `GET /listings?skip=0&limit=50&mingit _price=400000&max_price=2000000&min_year=2018&location=Manila`
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

- Base URL variable: `{{baseUrl}} = http://127.0.0.1:8000`
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
{your path}\venv\Scripts\python.exe - << 'PY'
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
